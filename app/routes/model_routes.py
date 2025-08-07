from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from app.service.model import ModelService

def create_model_route() -> APIRouter:
    router = APIRouter(
        prefix="/model"
    )


    @router.post("/")
    async def model_response(    
        case_id: str = Form(...),
        files: List[UploadFile] = File(...)
    ) -> Dict[str, Any]:
        try:
            manual_input = ""
            model_service = ModelService()
            result = await model_service.generate_response(
                files,
                manual_input,
                case_id
            )
            return JSONResponse({"result": result}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    return router