from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.model_routes import create_model_route

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
    
    app.include_router(create_model_route())

    @app.get("/")
    def healthcheck():
        return {"message": "api running"}

    return app


app = create_application()
