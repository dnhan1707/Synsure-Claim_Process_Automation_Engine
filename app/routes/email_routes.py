from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.schema.schema import EmailRequest
from app.service.email import EmailService

email_service = EmailService()

def create_email_route() -> APIRouter:
    router = APIRouter(
        prefix="/email"
    )

    @router.post("/")
    async def send_email(data: EmailRequest):
        try:
            await email_service.send_email(data)
            return JSONResponse({"success": True})
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    return router
