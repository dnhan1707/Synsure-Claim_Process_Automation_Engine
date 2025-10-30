import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from passlib.context import CryptContext
from supabase import Client, create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class AuthService:
    def __init__(self):
        # Supabase client (use your existing settings)
        setting = get_settings()
        sp = setting.supabase
        env = getattr(setting, "env", None)
        if env == "development":
            url, key = sp.url_development, sp.api_key_development
        else:
            url, key = sp.url, sp.api_key

        if not url or not key:
            raise RuntimeError("Supabase URL/API key not configured")
        self.db: Client = create_client(url, key)

        # JWT
        self.secret_key = os.getenv("SECRET_KEY")
        if not self.secret_key:
            logger.critical("SECRET_KEY is not set")
            raise RuntimeError("SECRET_KEY is required")

        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def _create_access_token(self, *, user_id: str, email: str, tenant_id: Optional[str], role: str) -> str:
        to_encode = {
            "sub": user_id,
            "email": email,
            "tenant_id": tenant_id,
            "role": role,
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(minutes=self.access_token_minutes)).timestamp()),
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        res = (
            self.db.table("app_users")
            .select("id, email, password_hash, role, tenant_id")
            .ilike("email", email)  # case-insensitive
            .limit(1)
            .execute()
        )
        data = res.data or []
        return data[0] if data else None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.db.table("app_users")
            .select("id, email, role, tenant_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        data = res.data or []
        return data[0] if data else None

    async def sign_up(self, email: str, password: str, tenant_id: Optional[str] = None, role: str = "viewer") -> Dict[str, Any]:
        email = email.strip().lower()
        if not EMAIL_RE.match(email):
            return {"error": "invalid_email"}

        if not password or len(password) < 8:
            return {"error": "weak_password", "message": "Password must be at least 8 characters"}

        existing = await self.get_user_by_email(email)
        if existing:
            return {"error": "email_taken"}

        password_hash = self._hash_password(password)

        obj = {
            "email": email,
            "password_hash": password_hash,
            "role": role or "viewer",
        }
        if tenant_id or tenant_id != "":
            obj["tenant_id"] = tenant_id

        res = self.db.table("app_users").insert(obj).execute()
        user = res.data[0] if res.data else None
        if not user:
            logger.error("Failed to insert user")
            return {"error": "signup_failed"}

        token = self._create_access_token(
            user_id=user["id"], email=user["email"], tenant_id=user.get("tenant_id"), role=user.get("role", "viewer")
        )
        return {
            "user": {"id": user["id"], "email": user["email"], "tenant_id": user.get("tenant_id"), "role": user.get("role", "viewer")},
            "access_token": token,
            "token_type": "bearer",
        }

    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        email = email.strip().lower()
        user = await self.get_user_by_email(email)
        if not user or not self._verify_password(password, user["password_hash"]):
            return {"error": "invalid_credentials"}

        token = self._create_access_token(
            user_id=user["id"], email=user["email"], tenant_id=user.get("tenant_id"), role=user.get("role", "viewer")
        )
        return {
            "user": {"id": user["id"], "email": user["email"], "tenant_id": user.get("tenant_id"), "role": user.get("role", "viewer")},
            "access_token": token,
            "token_type": "bearer",
        }

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except JWTError as e:
            logger.warning(f"JWT decode failed: {e}")
            return None