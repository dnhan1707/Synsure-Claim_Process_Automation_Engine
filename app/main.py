from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from app.routes.model_routes import create_model_route
from app.routes.email_routes import create_email_route
from app.routes.case_routes import create_case_route
from app.routes.case_routes_v2 import create_case_route_v2


def create_application() -> FastAPI:
    app = FastAPI(
        title="Startup Demo"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=False,  
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # app.include_router(create_model_route())
    app.include_router(create_email_route())
    # app.include_router(create_case_route())
    app.include_router(create_case_route_v2())

    @app.get("/")
    def healthcheck():
        return {"message": "api running"}
    
    return app


app = create_application()
