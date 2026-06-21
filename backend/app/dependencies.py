import logging
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk, JWTError, ExpiredSignatureError
 
from app.config import settings
 
logger = logging.getLogger("devselect")
 
bearer_scheme = HTTPBearer(auto_error=False)
 
def _configured_jwt_algorithms(value: str) -> tuple[str, ...]:
    algorithms = tuple(
        dict.fromkeys(
            algorithm.strip().upper()
            for algorithm in value.split(",")
            if algorithm.strip()
        )
    )
    if not algorithms:
        raise RuntimeError("SUPABASE_JWT_ALGORITHMS must configure at least one algorithm")
    if not all(algorithm.startswith(("ES", "RS", "PS")) for algorithm in algorithms):
        raise RuntimeError("SUPABASE_JWT_ALGORITHMS must contain only asymmetric JWKS algorithms")
    return algorithms


SUPABASE_JWT_ALGORITHMS = _configured_jwt_algorithms(settings.SUPABASE_JWT_ALGORITHMS)
SUPABASE_JWT_ISSUER = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"
JWKS_URL = f"{SUPABASE_JWT_ISSUER}/.well-known/jwks.json"
 
_jwks_cache: dict | None = None
 
 
async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(JWKS_URL)
                response.raise_for_status()
                _jwks_cache = response.json()
                logger.info("JWKS fetched and cached from Supabase")
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Supabase: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service temporarily unavailable",
            )
    return _jwks_cache
 
 
async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await verify_supabase_token(credentials.credentials)


async def verify_supabase_token(token: str) -> str:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        token_algorithm = unverified_header.get("alg")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (
        not isinstance(kid, str)
        or not kid
        or not isinstance(token_algorithm, str)
        or token_algorithm not in SUPABASE_JWT_ALGORITHMS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwks_data = await _get_jwks()
    matching_keys = [
        key
        for key in jwks_data.get("keys", [])
        if key.get("kid") == kid and key.get("alg") in SUPABASE_JWT_ALGORITHMS
    ]
 
    if not matching_keys:
        global _jwks_cache
        _jwks_cache = None
        jwks_data = await _get_jwks()
        matching_keys = [
            key
            for key in jwks_data.get("keys", [])
            if key.get("kid") == kid and key.get("alg") in SUPABASE_JWT_ALGORITHMS
        ]
 
    if not matching_keys:
        logger.warning("No matching allowed JWKS key found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    try:
        public_key = jwk.construct(matching_keys[0], algorithm=matching_keys[0]["alg"])
    except Exception as e:
        logger.error("Failed to construct public key from JWKS: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=list(SUPABASE_JWT_ALGORITHMS),
            audience=settings.SUPABASE_JWT_AUDIENCE,
            issuer=SUPABASE_JWT_ISSUER,
            options={
                "require_exp": True,
                "require_iat": True,
                "require_iss": True,
                "require_aud": True,
                "require_sub": True,
            },
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning("JWT verification failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    user_id = payload.get("sub")
    try:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError
        verified_user_id = str(UUID(user_id))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verified_user_id
