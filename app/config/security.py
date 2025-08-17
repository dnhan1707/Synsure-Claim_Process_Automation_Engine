from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

class SecuritySettings(BaseSettings):
    allowed_origins: List[str] = [
        origin for origin in [
            os.getenv("SEC_TEST_ORIGIN"), 
            os.getenv("SEC_DEPLOYMENT_ORIGIN"),
            os.getenv("SEC_TEST_FASTAPI_ORIGIN"),
            os.getenv("SEC_LOCAL_NETWORK_ORIGIN"),
            os.getenv("SEC_VERCEL_ORIGIN_1"),
            os.getenv("SEC_VERCEL_ORIGIN_2"),
            os.getenv("SEC_VERCEL_ORIGIN_3")
        ] if origin is not None  
    ]
    enable_cors: bool = True
    api_keys: List[str] = [key for key in [os.getenv("SEC_API_KEYS")] if key is not None]

security_setting = SecuritySettings()

def get_security_settings() -> SecuritySettings:
    return security_setting