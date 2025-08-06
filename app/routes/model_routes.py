from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, Any, List
from app.service.model import ModelService
from app.schema.schema import CaseMetadata

def create_model_route() -> APIRouter:
    router = APIRouter(
        prefix="/model"
    )


    @router.post("/")
    async def model_response(    
        case_id: str = Form(...),
        case_type: str = Form(...),
        files: List[UploadFile] = File(...)):
        try:
            model_service = ModelService()
            result = await model_service.generate_response(
                files,
                case_type,
                case_id
            )
            return {"result": result} 
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))



    return router