import asyncio
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import Settings, settings
from app.routers import health
from app.routers.evaluation import router as evaluation_router
from app.agents.graph import build_graph
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.circuit_breaker import CircuitBreakerMiddleware, admin_router
from app.middleware.error_handler import init_sentry, register_exception_handlers


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=1,
        max_size=10,
        open=False,
        check=AsyncConnectionPool.check_connection,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    ) as checkpoint_pool:
        checkpointer = AsyncPostgresSaver(checkpoint_pool)
        await checkpointer.setup()
        app.state.graph = build_graph(checkpointer)
        yield


def create_app(
    app_settings: Settings = settings,
    *,
    lifespan_handler=lifespan,
    initialize_observability: bool = True,
) -> FastAPI:
    docs_enabled = app_settings.api_docs_enabled
    app_kwargs = {
        "title": "DevSelect API",
        "description": "CV and GitHub evaluator for tech recruiters",
        "version": "1.0.0",
        "docs_url": "/docs" if docs_enabled else None,
        "redoc_url": "/redoc" if docs_enabled else None,
        "openapi_url": "/openapi.json" if docs_enabled else None,
    }
    if lifespan_handler is not None:
        app_kwargs["lifespan"] = lifespan_handler

    app = FastAPI(**app_kwargs)
    app.state.settings = app_settings

    if initialize_observability:
        init_sentry()

    register_exception_handlers(app)

    app.add_middleware(RateLimiterMiddleware)
    app.add_middleware(CircuitBreakerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.FRONTEND_URL, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(health.router)
    app.include_router(evaluation_router)

    # Keep operational controls opt-in. Deployments should additionally
    # restrict /admin at the network or platform layer where possible.
    if app_settings.ADMIN_ROUTES_ENABLED:
        app.include_router(admin_router)

    return app


app = create_app()
