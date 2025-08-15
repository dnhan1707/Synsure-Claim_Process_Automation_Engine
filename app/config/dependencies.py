from fastapi import Security, Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from app.config.security import get_security_settings, SecuritySettings
import secrets

API_KEY_HEADER = "x-api-key" 
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)

async def require_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
    settings: SecuritySettings = Depends(get_security_settings),
):
    # Let CORS preflight through
    if request.method == "OPTIONS":
        return

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    for valid_key in settings.api_keys:
        if valid_key and secrets.compare_digest(api_key, valid_key):
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "API-Key"},
    )