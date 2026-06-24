import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from starlette.requests import Request

from app.agents.agent3_lead_evaluator import GeminiQuotaExceededError
from app.config import settings
from app.middleware.circuit_breaker import CircuitBreakerMiddleware
from app.middleware.rate_limiter import (
    RateLimiterMiddleware,
    _anonymous_rate_limit_key,
    _rate_limit_key_for_request,
)
from app.models.requests import FollowUpRequest
from app.routers.evaluation import follow_up_question, upload_cv
from app.utils import budget_limits, evaluation_lock
from app.utils.api_responses import rate_limit_response
from app.utils.budget_limits import (
    BUDGET_REDIS_UNAVAILABLE,
    FOLLOWUP_EVALUATION_LIMIT_REACHED,
    FOLLOWUP_USER_DAILY_LIMIT_REACHED,
    GLOBAL_DAILY_EVALUATION_LIMIT_REACHED,
    GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED,
    USER_DAILY_EVALUATION_LIMIT_REACHED,
    USER_LIFETIME_EVALUATION_LIMIT_REACHED,
    BudgetDecision,
    EvaluationQuotaSnapshot,
    FollowUpQuotaSnapshot,
    check_evaluation_quota,
    check_follow_up_quota,
)
from app.utils.evaluation_lock import (
    EVALUATION_ALREADY_IN_PROGRESS,
    EvaluationLockDecision,
)
from app.utils.llm_provider import LLMProviderUnavailableError


def _request(path="/api/chat/chat-1/upload", *, headers=None, client_host="127.0.0.1"):
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers or [],
            "client": (client_host, 50000),
            "server": ("testserver", 80),
        }
    )


class QuotaPolicyTests(unittest.TestCase):
    def test_portfolio_beta_quota_defaults(self):
        self.assertEqual(settings.GLOBAL_EVALS_PER_DAY, 2)
        self.assertEqual(settings.GLOBAL_EVALS_PER_MONTH, 50)
        self.assertEqual(settings.USER_EVALS_PER_DAY, 1)
        self.assertEqual(settings.USER_EVALS_LIFETIME, 5)
        self.assertEqual(settings.FOLLOWUPS_PER_EVALUATION, 2)
        self.assertEqual(settings.FOLLOWUPS_PER_USER_DAY, 3)

    def test_user_daily_evaluation_quota(self):
        decision = check_evaluation_quota(
            EvaluationQuotaSnapshot(user_daily=settings.USER_EVALS_PER_DAY),
            100,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, USER_DAILY_EVALUATION_LIMIT_REACHED)
        self.assertGreater(decision.retry_after_seconds, 0)

    def test_user_lifetime_evaluation_quota(self):
        decision = check_evaluation_quota(
            EvaluationQuotaSnapshot(user_lifetime=settings.USER_EVALS_LIFETIME),
            100,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, USER_LIFETIME_EVALUATION_LIMIT_REACHED)

    def test_global_daily_evaluation_quota(self):
        decision = check_evaluation_quota(
            EvaluationQuotaSnapshot(global_daily=settings.GLOBAL_EVALS_PER_DAY),
            100,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, GLOBAL_DAILY_EVALUATION_LIMIT_REACHED)
        self.assertGreater(decision.retry_after_seconds, 0)

    def test_global_monthly_evaluation_quota(self):
        decision = check_evaluation_quota(
            EvaluationQuotaSnapshot(global_monthly=settings.GLOBAL_EVALS_PER_MONTH),
            100,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED)
        self.assertGreater(decision.retry_after_seconds, 0)

    def test_follow_up_quotas(self):
        per_evaluation = check_follow_up_quota(
            FollowUpQuotaSnapshot(
                evaluation_count=settings.FOLLOWUPS_PER_EVALUATION,
            )
        )
        per_user_day = check_follow_up_quota(
            FollowUpQuotaSnapshot(
                user_daily_count=settings.FOLLOWUPS_PER_USER_DAY,
            )
        )
        self.assertEqual(per_evaluation.code, FOLLOWUP_EVALUATION_LIMIT_REACHED)
        self.assertEqual(per_user_day.code, FOLLOWUP_USER_DAILY_LIMIT_REACHED)
        self.assertGreater(per_user_day.retry_after_seconds, 0)

    def test_standard_429_response_includes_code_and_retry_after(self):
        response = rate_limit_response(
            code="RATE_LIMIT_EXCEEDED",
            retry_after_seconds=17,
        )
        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "17")
        self.assertEqual(payload["code"], "RATE_LIMIT_EXCEEDED")
        self.assertEqual(payload["retry_after_seconds"], 17)


class AtomicRedisQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_evaluation_quota_uses_one_atomic_redis_eval(self):
        run_upstash = AsyncMock(return_value=["allowed", "OK"])
        with patch("app.utils.budget_limits._run_upstash", new=run_upstash):
            decision = await budget_limits._record_upstash_evaluation("user-1", 100)

        self.assertTrue(decision.allowed)
        payload = run_upstash.await_args.args[0]
        self.assertEqual(payload[0], "EVAL")
        self.assertEqual(payload[2], 6)
        self.assertIn("USER_LIFETIME_EVALUATION_LIMIT_REACHED", payload[1])
        self.assertIn('redis.call("SET", KEYS[6]', payload[1])

    async def test_follow_up_quota_uses_one_atomic_redis_eval(self):
        run_upstash = AsyncMock(return_value=["allowed", "OK"])
        with patch("app.utils.budget_limits._run_upstash", new=run_upstash):
            decision = await budget_limits._record_upstash_follow_up(
                "user-1",
                "chat-1",
            )

        self.assertTrue(decision.allowed)
        payload = run_upstash.await_args.args[0]
        self.assertEqual(payload[0], "EVAL")
        self.assertEqual(payload[2], 2)
        self.assertIn("FOLLOWUP_EVALUATION_LIMIT_REACHED", payload[1])

    async def test_budget_redis_failure_fails_closed_in_production(self):
        with (
            patch.object(settings, "APP_ENV", "production"),
            patch("app.utils.budget_limits._upstash_configured", return_value=True),
            patch(
                "app.utils.budget_limits._record_upstash_evaluation",
                new=AsyncMock(side_effect=RuntimeError("redis unavailable")),
            ),
        ):
            decision = await budget_limits.record_evaluation_usage("user-1", 100)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, BUDGET_REDIS_UNAVAILABLE)


class EvaluationLockTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        evaluation_lock._memory_locks.clear()

    async def asyncTearDown(self):
        evaluation_lock._memory_locks.clear()

    async def test_redis_lock_uses_set_nx_with_expiry(self):
        response = SimpleNamespace(status_code=200, json=lambda: {"result": "OK"})
        post = AsyncMock(return_value=response)
        with (
            patch("app.utils.evaluation_lock._redis_configured", return_value=True),
            patch.object(evaluation_lock._http_client, "post", new=post),
        ):
            decision = await evaluation_lock.acquire_evaluation_lock("chat-1")

        self.assertTrue(decision.allowed)
        command = post.await_args.kwargs["json"]
        self.assertEqual(command[0], "SET")
        self.assertIn("NX", command)
        self.assertIn("EX", command)

    async def test_duplicate_evaluation_is_blocked_until_owner_releases(self):
        with (
            patch.object(settings, "APP_ENV", "development"),
            patch("app.utils.evaluation_lock._redis_configured", return_value=False),
        ):
            first = await evaluation_lock.acquire_evaluation_lock("chat-1")
            duplicate = await evaluation_lock.acquire_evaluation_lock("chat-1")
            wrong_release = await evaluation_lock.release_evaluation_lock(
                "chat-1",
                "wrong-token",
            )
            released = await evaluation_lock.release_evaluation_lock(
                "chat-1",
                first.token,
            )
            next_attempt = await evaluation_lock.acquire_evaluation_lock("chat-1")

        self.assertTrue(first.allowed)
        self.assertFalse(duplicate.allowed)
        self.assertEqual(duplicate.code, EVALUATION_ALREADY_IN_PROGRESS)
        self.assertFalse(wrong_release)
        self.assertTrue(released)
        self.assertTrue(next_attempt.allowed)

    async def test_only_one_stream_can_claim_an_admission_lock(self):
        with (
            patch.object(settings, "APP_ENV", "development"),
            patch("app.utils.evaluation_lock._redis_configured", return_value=False),
        ):
            admission = await evaluation_lock.acquire_evaluation_lock("chat-1")
            first_stream = await evaluation_lock.claim_evaluation_stream(
                "chat-1",
                admission.token,
            )
            duplicate_stream = await evaluation_lock.claim_evaluation_stream(
                "chat-1",
                admission.token,
            )
            released = await evaluation_lock.release_evaluation_lock(
                "chat-1",
                first_stream,
            )

        self.assertIsNotNone(first_stream)
        self.assertIsNone(duplicate_stream)
        self.assertTrue(released)

    async def test_lock_failure_fails_closed_in_production(self):
        with (
            patch.object(settings, "APP_ENV", "production"),
            patch("app.utils.evaluation_lock._redis_configured", return_value=True),
            patch.object(
                evaluation_lock._http_client,
                "post",
                new=AsyncMock(side_effect=RuntimeError("redis unavailable")),
            ),
        ):
            decision = await evaluation_lock.acquire_evaluation_lock("chat-1")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, evaluation_lock.EVALUATION_LOCK_UNAVAILABLE)


class MiddlewareSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_rate_limit_key_hashes_user_id(self):
        user_id = "123e4567-e89b-42d3-a456-426614174000"
        request = _request(headers=[(b"authorization", b"Bearer test-token")])

        with patch(
            "app.middleware.rate_limiter.verify_supabase_token",
            new=AsyncMock(return_value=user_id),
        ):
            key = await _rate_limit_key_for_request(request)

        digest = key.removeprefix("rate_limit:user:")
        self.assertTrue(key.startswith("rate_limit:user:"))
        self.assertNotIn(user_id, key)
        self.assertEqual(len(digest), 64)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    async def test_anonymous_rate_limit_key_hashes_client_ip(self):
        client_ip = "203.0.113.42"
        key = _anonymous_rate_limit_key(_request(client_host=client_ip))

        digest = key.removeprefix("rate_limit:anonymous:")
        self.assertTrue(key.startswith("rate_limit:anonymous:"))
        self.assertNotIn(client_ip, key)
        self.assertEqual(len(digest), 64)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    async def test_rate_limiter_denial_keeps_429_retry_after_behavior(self):
        middleware = RateLimiterMiddleware(lambda scope, receive, send: None)
        call_next = AsyncMock()

        with (
            patch(
                "app.middleware.rate_limiter._rate_limit_key_for_request",
                new=AsyncMock(return_value="rate_limit:user:" + "a" * 64),
            ),
            patch(
                "app.middleware.rate_limiter._run_lua_on_upstash",
                new=AsyncMock(return_value=("denied", 17)),
            ),
        ):
            response = await middleware.dispatch(_request(), call_next)

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "17")
        self.assertEqual(response.headers["X-RateLimit-Limit"], "10")
        self.assertEqual(response.headers["X-RateLimit-Remaining"], "0")
        self.assertEqual(payload["code"], "RATE_LIMIT_EXCEEDED")
        self.assertEqual(payload["retry_after_seconds"], 17)
        call_next.assert_not_awaited()

    async def test_rate_limiter_redis_failure_fails_closed_in_production(self):
        middleware = RateLimiterMiddleware(lambda scope, receive, send: None)
        call_next = AsyncMock()
        with (
            patch.object(settings, "APP_ENV", "production"),
            patch.object(settings, "RATE_LIMIT_FAIL_OPEN", True),
            patch(
                "app.middleware.rate_limiter._rate_limit_key_for_request",
                new=AsyncMock(return_value="rate-limit-key"),
            ),
            patch(
                "app.middleware.rate_limiter._run_lua_on_upstash",
                new=AsyncMock(side_effect=RuntimeError("redis unavailable")),
            ),
        ):
            response = await middleware.dispatch(_request(), call_next)

        self.assertEqual(response.status_code, 503)
        call_next.assert_not_awaited()

    async def test_open_circuit_blocks_provider_route(self):
        middleware = CircuitBreakerMiddleware(lambda scope, receive, send: None)
        call_next = AsyncMock()
        with patch(
            "app.middleware.circuit_breaker._get_flag",
            new=AsyncMock(return_value="true"),
        ):
            response = await middleware.dispatch(_request(), call_next)

        self.assertEqual(response.status_code, 503)
        call_next.assert_not_awaited()

    async def test_circuit_redis_failure_fails_closed_in_production(self):
        middleware = CircuitBreakerMiddleware(lambda scope, receive, send: None)
        call_next = AsyncMock()
        with (
            patch.object(settings, "APP_ENV", "production"),
            patch.object(settings, "CIRCUIT_BREAKER_FAIL_OPEN", True),
            patch(
                "app.middleware.circuit_breaker._get_flag",
                new=AsyncMock(side_effect=RuntimeError("redis unavailable")),
            ),
        ):
            response = await middleware.dispatch(_request(), call_next)

        self.assertEqual(response.status_code, 503)
        call_next.assert_not_awaited()


class EndpointSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_quota_failure_uses_standard_429_contract(self):
        quota_error = GeminiQuotaExceededError(
            "test-model",
            RuntimeError("provider quota"),
            retry_after_seconds=31,
        )
        with (
            patch(
                "app.routers.evaluation._load_completed_report_for_chat",
                new=AsyncMock(return_value="completed report"),
            ),
            patch(
                "app.routers.evaluation.record_follow_up_usage",
                new=AsyncMock(
                    return_value=BudgetDecision(
                        allowed=True,
                        storage="test",
                        scope="follow_up",
                    )
                ),
            ),
            patch(
                "app.routers.evaluation._generate_follow_up_answer",
                new=AsyncMock(side_effect=quota_error),
            ),
        ):
            response = await follow_up_question(
                "chat-1",
                FollowUpRequest(question="What changes?"),
                "user-1",
            )

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "31")
        self.assertEqual(payload["code"], "GEMINI_QUOTA_EXCEEDED")

    async def test_generic_provider_rate_limit_uses_standard_429_contract(self):
        quota_error = LLMProviderUnavailableError(
            "groq",
            "test-model",
            RuntimeError("provider quota"),
            status_code=429,
            provider_status="RATE_LIMITED",
            retry_after_seconds=29,
        )
        with (
            patch(
                "app.routers.evaluation._load_completed_report_for_chat",
                new=AsyncMock(return_value="completed report"),
            ),
            patch(
                "app.routers.evaluation.record_follow_up_usage",
                new=AsyncMock(
                    return_value=BudgetDecision(
                        allowed=True,
                        storage="test",
                        scope="follow_up",
                    )
                ),
            ),
            patch(
                "app.routers.evaluation._generate_follow_up_answer",
                new=AsyncMock(side_effect=quota_error),
            ),
        ):
            response = await follow_up_question(
                "chat-1",
                FollowUpRequest(question="What changes?"),
                "user-1",
            )

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "29")
        self.assertEqual(payload["code"], "GROQ_RATE_LIMITED")

    async def test_upload_pre_stream_failure_releases_evaluation_lock(self):
        graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=RuntimeError("graph failed")))
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(graph=graph)),
        )
        release_lock = AsyncMock(return_value=True)
        with (
            patch(
                "app.routers.evaluation._get_owned_chat",
                new=AsyncMock(
                    return_value={
                        "id": "chat-1",
                        "user_id": "user-1",
                        "thread_id": None,
                    }
                ),
            ),
            patch(
                "app.routers.evaluation._read_validated_pdf_upload",
                new=AsyncMock(return_value=(b"%PDF-test", "CV preview")),
            ),
            patch(
                "app.routers.evaluation._graph_thread_has_state",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "app.routers.evaluation.acquire_evaluation_lock",
                new=AsyncMock(
                    return_value=EvaluationLockDecision(
                        allowed=True,
                        token="lock-token",
                    )
                ),
            ),
            patch(
                "app.routers.evaluation._save_chat_thread_id",
                new=AsyncMock(),
            ),
            patch(
                "app.routers.evaluation.record_evaluation_usage",
                new=AsyncMock(
                    return_value=BudgetDecision(
                        allowed=True,
                        storage="test",
                        scope="evaluation",
                    )
                ),
            ),
            patch("app.routers.evaluation._write_temp_pdf", return_value="temp.pdf"),
            patch("app.routers.evaluation._delete_temp_file"),
            patch(
                "app.routers.evaluation.release_evaluation_lock",
                new=release_lock,
            ),
            patch.object(settings, "DEV_MOCK_EVALUATION", False),
        ):
            with self.assertRaises(RuntimeError):
                await upload_cv(
                    "chat-1",
                    request,
                    SimpleNamespace(),
                    None,
                    None,
                    None,
                    "user-1",
                )

        release_lock.assert_awaited_once_with("chat-1", "lock-token")


if __name__ == "__main__":
    unittest.main()
