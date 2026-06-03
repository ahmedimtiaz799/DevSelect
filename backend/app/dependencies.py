import logging
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk, JWTError, ExpiredSignatureError
 
from app.config import settings
 
logger = logging.getLogger("devselect")
 
bearer_scheme = HTTPBearer(auto_error=False)
 
JWKS_URL = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
 
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
        alg = unverified_header.get("alg", "ES256")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    jwks_data = await _get_jwks()
    matching_keys = [k for k in jwks_data.get("keys", []) if k.get("kid") == kid]
 
    if not matching_keys:
        global _jwks_cache
        _jwks_cache = None
        jwks_data = await _get_jwks()
        matching_keys = [k for k in jwks_data.get("keys", []) if k.get("kid") == kid]
 
    if not matching_keys:
        logger.error(f"No matching JWKS key found for kid={kid}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    try:
        public_key = jwk.construct(matching_keys[0])
    except Exception as e:
        logger.error(f"Failed to construct public key from JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[alg],
            options={"verify_aud": False},
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    return user_id
