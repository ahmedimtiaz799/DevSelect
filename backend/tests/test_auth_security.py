import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from jose import jwk, jwt

from app.config import settings
from app.dependencies import (
    SUPABASE_JWT_ALGORITHMS,
    SUPABASE_JWT_ISSUER,
    verify_supabase_token,
)
from app.routers.evaluation import _assert_chat_thread, _get_owned_chat


class _FakeChatQuery:
    def __init__(self, chat):
        self.chat = chat
        self.filters = {}

    def select(self, _columns):
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def limit(self, _count):
        return self

    async def execute(self):
        matches = self.chat and all(
            str(self.chat.get(column)) == str(value)
            for column, value in self.filters.items()
        )
        return SimpleNamespace(data=[self.chat] if matches else [])


class _FakeSupabase:
    def __init__(self, chat):
        self.chat = chat

    def table(self, table_name):
        if table_name != "chats":
            raise AssertionError(f"Unexpected table: {table_name}")
        return _FakeChatQuery(self.chat)


class SupabaseJwtSecurityTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        private_key = ec.generate_private_key(ec.SECP256R1())
        cls.private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        cls.key_id = "test-es256-key"
        cls.public_jwk = jwk.construct(public_key, algorithm="ES256").to_dict()
        cls.public_jwk.update({"kid": cls.key_id, "alg": "ES256", "use": "sig"})

    def _claims(self, **overrides):
        now = int(time.time())
        claims = {
            "sub": str(uuid4()),
            "aud": settings.SUPABASE_JWT_AUDIENCE,
            "iss": SUPABASE_JWT_ISSUER,
            "iat": now,
            "exp": now + 300,
        }
        claims.update(overrides)
        return claims

    def _token(self, claims=None, algorithm="ES256", key=None):
        return jwt.encode(
            claims or self._claims(),
            key or self.private_key,
            algorithm=algorithm,
            headers={"kid": self.key_id},
        )

    async def _assert_rejected(self, token, expected_detail="Invalid token"):
        with patch(
            "app.dependencies._get_jwks",
            new=AsyncMock(return_value={"keys": [self.public_jwk]}),
        ):
            with self.assertRaises(HTTPException) as context:
                await verify_supabase_token(token)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, expected_detail)

    async def test_valid_supabase_like_token_returns_uuid_subject(self):
        user_id = str(uuid4())
        token = self._token(self._claims(sub=user_id))

        with patch(
            "app.dependencies._get_jwks",
            new=AsyncMock(return_value={"keys": [self.public_jwk]}),
        ):
            verified_user_id = await verify_supabase_token(token)

        self.assertEqual(verified_user_id, user_id)
        self.assertEqual(SUPABASE_JWT_ALGORITHMS, ("ES256",))

    async def test_expired_token_is_rejected(self):
        now = int(time.time())
        token = self._token(self._claims(iat=now - 600, exp=now - 300))

        await self._assert_rejected(token, expected_detail="Token has expired")

    async def test_wrong_issuer_is_rejected(self):
        token = self._token(self._claims(iss="https://invalid.example/auth/v1"))

        await self._assert_rejected(token)

    async def test_wrong_audience_is_rejected(self):
        token = self._token(self._claims(aud="anon"))

        await self._assert_rejected(token)

    async def test_missing_subject_is_rejected(self):
        claims = self._claims()
        claims.pop("sub")

        await self._assert_rejected(self._token(claims))

    async def test_non_uuid_subject_is_rejected(self):
        token = self._token(self._claims(sub="not-a-uuid"))

        await self._assert_rejected(token, expected_detail="Invalid token payload")

    async def test_missing_expiration_is_rejected(self):
        claims = self._claims()
        claims.pop("exp")

        await self._assert_rejected(self._token(claims))

    async def test_missing_issued_at_is_rejected(self):
        claims = self._claims()
        claims.pop("iat")

        await self._assert_rejected(self._token(claims))

    async def test_unsupported_symmetric_algorithm_is_rejected(self):
        token = self._token(
            algorithm="HS256",
            key="test-only-shared-secret",
        )

        await self._assert_rejected(token)


class ChatAuthorizationBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_cross_user_chat_id_is_blocked(self):
        owner_id = str(uuid4())
        requesting_user_id = str(uuid4())
        chat = {
            "id": str(uuid4()),
            "user_id": owner_id,
            "thread_id": "owner-thread",
        }

        with patch(
            "app.routers.evaluation.get_supabase",
            new=AsyncMock(return_value=_FakeSupabase(chat)),
        ):
            with self.assertRaises(HTTPException) as context:
                await _get_owned_chat(chat["id"], requesting_user_id)

        self.assertEqual(context.exception.status_code, 403)

    async def test_mismatched_thread_id_is_blocked(self):
        chat = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "thread_id": "stored-thread",
        }

        with self.assertRaises(HTTPException) as context:
            _assert_chat_thread(chat, "different-thread")

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
