from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routes.email_routes import create_email_route
from app.routes.case_routes import create_case_route
from app.config.security import security_setting
from app.config.dependencies import require_api_key

def create_application() -> FastAPI:
    app = FastAPI(title="Synsure")

    if security_setting.enable_cors and security_setting.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=security_setting.allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  
            allow_headers=["Authorization", "Content-Type", "X-Request-ID", "x-api-key", "*"],  
        )

        app.include_router(create_email_route(), dependencies=[Depends(require_api_key)])
        app.include_router(create_case_route(), dependencies=[Depends(require_api_key)])
        return app

app = create_application()