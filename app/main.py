from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routes.email_routes import create_email_route
from app.routes.tenant_routes import create_tenant_routes
from app.routes.claim_manager_route import create_claim_manager_routes
from app.routes.case_routes_v2 import create_case_routes_v2
from app.routes.case_routes_v2 import create_case_routes_v3
from app.routes.submission_routes import create_submission_routes2
from app.routes.file_routes import create_file_routes_v2
from app.routes.task_routes import create_task_router
from app.routes.insight_routes import create_insight_route
from app.routes.dashboard_routes import create_dashboard_route
from app.config.dependencies import require_api_key
from app.config.security import security_setting


def create_application() -> FastAPI:
    app = FastAPI(
        title="Synsure API",
        description="""
        ## Synsure Insurance Claims Processing API
        
        This API provides comprehensive insurance claims processing capabilities including:
        
        * **Tenant Management** - Manage tenant organizations
        * **Claims Management** - Create and manage insurance claims
        * **Case Processing** - Handle individual case workflows  
        * **File Management** - Upload, manage, and process claim documents
        * **AI Processing** - Submit cases for AI analysis and processing
        * **Task Management** - Monitor background processing tasks
        * **Email Services** - Handle email notifications and communications
        
        ### Authentication
        All endpoints require an API key in the `x-api-key` header.
        """,
        version="2.0.0",
        license_info={
            "name": "MIT License",
        },
        # Custom tag ordering
        tags_metadata=[
            {
                "name": "Tenants",
                "description": "Manage tenant organizations and accounts",
            },
            {
                "name": "Claims",
                "description": "Create and manage insurance claims",
            },
            {
                "name": "Cases", 
                "description": "Handle individual case workflows and data",
            },
            {
                "name": "Files",
                "description": "Upload, manage, and process claim documents",
            },
            {
                "name": "AI Processing",
                "description": "Submit cases for AI analysis and get results",
            },
            {
                "name": "Tasks",
                "description": "Monitor background processing and batch operations",
            },
            {
                "name": "Email",
                "description": "Email notifications and communications",
            },
            {                
                "name": "Insight",
                "description": "Provide meaningful metrics",
            },
            {
                "name": "Debug",
                "description": "Development and debugging utilities",
            },
        ]
    )

    if security_setting.enable_cors and security_setting.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=security_setting.allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  
            allow_headers=["Authorization", "Content-Type", "X-Request-ID", "x-api-key", "*"],  
        )

    # Include routers in logical order
    app.include_router(create_tenant_routes(), dependencies=[Depends(require_api_key)])
    app.include_router(create_claim_manager_routes(), dependencies=[Depends(require_api_key)])
    app.include_router(create_case_routes_v2(), dependencies=[Depends(require_api_key)])
    app.include_router(create_case_routes_v3(), dependencies=[Depends(require_api_key)])
    app.include_router(create_file_routes_v2(), dependencies=[Depends(require_api_key)])
    app.include_router(create_submission_routes2(), dependencies=[Depends(require_api_key)])
    app.include_router(create_task_router(), dependencies=[Depends(require_api_key)])
    app.include_router(create_insight_route(), dependencies=[Depends(require_api_key)])
    app.include_router(create_dashboard_route(), dependencies=[Depends(require_api_key)])
    app.include_router(create_email_route(), dependencies=[Depends(require_api_key)])

    return app

app = create_application()