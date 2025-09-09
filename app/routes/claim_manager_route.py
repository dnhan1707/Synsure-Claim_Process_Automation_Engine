from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import APIRouter, UploadFile, File, Form
from typing import List
from app.controller.claim_manager_controller import ClaimManagerController


claim_manager_controller = ClaimManagerController()

def create_claim_manager_routes() -> APIRouter:
    router = APIRouter(
        prefix="/claim/manager"
    )
    
    
    @router.post("/")
    async def create_new_claim(
        tenant_id: str,
        case_name: str,
        manual_input: str = Form(None),
        files: List[UploadFile] = File(None)
    ):
        # create and upload files, if no files. just create a case
        try:
            res = await claim_manager_controller.create_new_claim(
                tenant_id=tenant_id,
                case_name=case_name,
                manual_input=manual_input,
                files=files
            )
            if not res:
                return JSONResponse({"success": False, "error": "create_new_claim"}, status_code=500) 

            return JSONResponse({"success": True}, status_code=200)
        
        except Exception as e:
            return JSONResponse({"success": False, "error": e}, status_code=500) 

    
    async def get_claim(id: str):
        pass

    
    async def get_all_claims():
        pass

    
    async def update_claim_name(id: str, new_name: str):
        pass

    
    async def upload_files_existed_case(
        id: str,         
        manual_input: str = Form(None),
        files: List[UploadFile] = File(None)
    ):
        pass
    
    
    async def replace_existed_file(
        id: str,
        file_id: str,
        new_file: UploadFile
    ):
        pass

    
    async def remove_files(ids: List[str]):
        pass

    
    async def remove_case(id: str):
        pass



    return router
