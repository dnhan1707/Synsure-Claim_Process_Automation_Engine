from fastapi import APIRouter, UploadFile
from fastapi.responses import JSONResponse
from app.service.case_service_v2 import CaseService
from app.service.submission_service import SubmissionService

case_service = CaseService()
submission_service = SubmissionService()


def create_submission_routes2() -> APIRouter:
    router = APIRouter(prefix="/api/v1/submission")

    '''
    POST "/": create a new case (case_id exist means that's old case), and run with files (does not apply if no file) 
    Body: 
        {
            tenant_id: str
            case_id: Optional[str] # if None, meaning new case
            case_name: str
            files: list[UploadFile] = Form(...)
        }
    return: Dict {success: bool, result: {}}

    '''
    @router.post("/newcase")
    async def submit_new_case(
        tenant_id: str, 
        case_name: str, 
        files: list[UploadFile],
    ):

        try:
            new_case_id, model_response = await submission_service.submit_new_case(
                tenant_id, case_name, files
            )

            if not new_case_id or not model_response:
                return JSONResponse({"success": False, "new_case_id": "", "result": {}}, status_code=500)

            return JSONResponse({"success": True, "new_case_id": new_case_id, "result": model_response}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    '''
    POST "/start": run with chosen files
    Body: 
        {
            tenant_id: str
            case_id: str
            chosen_files: list[ids]
        } 
    '''
    @router.post("/start")
    async def submit_with_chosen_files(
        tenant_id: str,
        case_id: str,
        chosen_files: list[str]
    ): 
        try:
            model_response = await submission_service.submit_with_chosen_files(
                tenant_id, case_id, chosen_files
            )
            
            # ✅ Check if we got valid response
            if not model_response or model_response == {}:
                return JSONResponse({"success": False, "error": "No content generated"}, status_code=500)
                
            return JSONResponse({"success": True, "result": model_response}, status_code=200)  # ✅ Fixed

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        
    return router
