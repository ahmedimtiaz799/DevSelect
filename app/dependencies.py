from fastapi import HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer(auto_error=False)

async def verify_jwt_token(
        credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme)
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing. Please include Authorization header with Bearer token.",
            headers={"WWW-Authenticate":"Bearer"},
        )

  
    raise NotImplementedError(
        "Jwt Verification is not implemented yet."
    )