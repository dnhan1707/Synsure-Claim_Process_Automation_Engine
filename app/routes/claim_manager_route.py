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
        files: List[UploadFile] = File(None)
    ):
        # create and upload files, if no files. just create a case
        try:
            res = await claim_manager_controller.create_new_claim(
                tenant_id=tenant_id,
                case_name=case_name,
                files=files
            )
            if not res:
                return JSONResponse({"success": False, "error": "create_new_claim"}, status_code=500) 

            return JSONResponse({"success": True}, status_code=200)
        
        except Exception as e:
            return JSONResponse({"success": False, "error": e}, status_code=500) 

    
    @router.get("/{id}")
    async def get_claim_by_id(id: str):
        try:
            res = await claim_manager_controller.get_claim_by_id(id)
            if not res:
                return JSONResponse({"success": False, "result": {}, "error": "get_claim_by_id"}, status_code=500) 

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "result": {}, "error": e}, status_code=500) 


    @router.get("/")
    async def get_all_claim():
        try:
            res = await claim_manager_controller.get_all_claim()
            if not res:
                return JSONResponse({"success": False, "result": [], "error": "get_all_claim"}, status_code=500) 

            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "result": [], "error": e}, status_code=500) 

    
    @router.patch("/{id}")
    async def update_claim_name(id: str, new_name: str):
        try:
            res = await claim_manager_controller.update_claim_name(id, new_name)
            if not res:
                return JSONResponse({"success": False, "error": "update_claim_name"}, status_code=500) 

            return JSONResponse({"success": True}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": e}, status_code=500) 

    
    @router.post("/{tenant_id}/{case_id}")
    async def upload_files_existed_case(
        tenant_id: str,
        case_id: str,         
        files: List[UploadFile] = File(...)
    ):
        try:
            res = await claim_manager_controller.upload_files_existed_case(tenant_id, case_id, files)
            if not res:
                return JSONResponse({"success": False, "error": "upload_files_existed_case"}, status_code=500) 

            return JSONResponse({"success": True}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": e}, status_code=500) 

    
    
    @router.put("/{tenant_id}/{case_id}/{file_id}")
    async def replace_existed_file(
        tenant_id: str,
        case_id: str,
        file_id: str,
        new_file: UploadFile
    ):
        try:
            res = await claim_manager_controller.replace_existed_file(tenant_id, case_id, file_id, new_file)
            if not res:
                return JSONResponse({"success": False, "error": "replace_existed_file"}, status_code=500) 

            return JSONResponse({"success": True}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": e}, status_code=500) 

    
    
    @router.delete("/files")
    async def remove_files(file_ids: List[str]):
        """
        Remove multiple files by their IDs
        Request body: ["file_id_1", "file_id_2", "file_id_3"]
        """
        try:            
            if not file_ids:
                return JSONResponse(
                    {"success": False, "error": "No file IDs provided"}, 
                    status_code=400
                )
            
            res = await claim_manager_controller.remove_files(file_ids)
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to remove some or all files"}, 
                    status_code=500
                ) 

            return JSONResponse(
                {"success": True, "message": f"Successfully deleted {len(file_ids)} files"}, 
                status_code=200
            )

        except Exception as e:
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            ) 


    @router.delete("/{case_id}")
    async def remove_case(case_id: str):
        """
        Remove a case and all its associated files
        """
        try:            
            res = await claim_manager_controller.remove_case(case_id)
            if not res:
                return JSONResponse(
                    {"success": False, "error": "Failed to remove case"}, 
                    status_code=500
                ) 

            return JSONResponse(
                {"success": True, "message": "Case successfully deleted"}, 
                status_code=200
            )

        except Exception as e:
            return JSONResponse(
                {"success": False, "error": "Internal server error"}, 
                status_code=500
            )




    return router
