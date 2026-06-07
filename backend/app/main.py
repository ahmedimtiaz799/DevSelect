import asyncio
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings
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


app = FastAPI(
    title="DevSelect API",
    description="CV and GitHub evaluator for tech recruiters",
    version="1.0.0",
    lifespan=lifespan,
)

init_sentry()

register_exception_handlers(app)

app.add_middleware(RateLimiterMiddleware)

app.add_middleware(CircuitBreakerMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(evaluation_router)
app.include_router(admin_router)
