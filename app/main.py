from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routes.model_routes import create_model_route
from email.mime.text import MIMEText
from app.schema.schema import EmailRequest
from dotenv import load_dotenv
import smtplib
import os

DEMO_EMAIL_USER=os.getenv("DEMO_EMAIL_USER")
DEMO_EMAIL_PASS=os.getenv("DEMO_EMAIL_PASS")


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


    @app.post("/email")
    async def send_email(data: EmailRequest):

        # Compose email
        body = f"Name: {data.name}\n Company: {data.company} \nEmail: {data.email}\nMessage: {data.message}"
        msg = MIMEText(body)
        msg["Subject"] = "Demo Request"
        msg["From"] = data.email
        msg["To"] = DEMO_EMAIL_USER

        # Send email (use your credentials)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(DEMO_EMAIL_USER, DEMO_EMAIL_PASS)
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())
            return JSONResponse({"success": True})
        except Exception as e:
            print("Email error:", e)
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    return app


app = create_application()
