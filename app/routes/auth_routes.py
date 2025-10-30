from fastapi import APIRouter, Depends, HTTPException, status, Header, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
import logging

from app.service.auth_service import AuthService

logger = logging.getLogger(__name__)
auth_service = AuthService()

http_bearer = HTTPBearer(auto_error=False)  # don’t auto-403; we’ll return 401 with a clear message

class SignUpBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    tenant_id: Optional[str] = None
    role: Optional[str] = Field(default="viewer")

class SignInBody(BaseModel):
    email: EmailStr
    password: str

def create_auth_routes() -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

    @router.post("/signup")
    async def sign_up(body: SignUpBody):
        res = await auth_service.sign_up(body.email, body.password, body.tenant_id, body.role or "viewer")
        if "error" in res:
            code = 400 if res["error"] in ("invalid_email", "weak_password", "email_taken") else 500
            return JSONResponse({"success": False, "error": res["error"], "result": {}}, status_code=code)
        return JSONResponse({"success": True, "result": res}, status_code=201)

    @router.post("/signin")
    async def sign_in(body: SignInBody):
        res = await auth_service.sign_in(body.email, body.password)
        if "error" in res:
            return JSONResponse({"success": False, "error": res["error"], "result": {}}, status_code=401)
        return JSONResponse({"success": True, "result": res}, status_code=200)

    # Optional helper to validate a token quickly
    @router.get("/whoami")
    async def whoami(claims = Security(get_current_user)):
        return {"success": True, "result": claims}

    return router

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(http_bearer)):
    """
    Validates Bearer token from Authorization header.
    Works with Swagger 'Authorize' button.
    """
    if not credentials or (credentials.scheme or "").lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization scheme")
    token = credentials.credentials
    claims = auth_service.decode_token(token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return claims