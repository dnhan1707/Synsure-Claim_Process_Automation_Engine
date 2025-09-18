from app.controller.case_controller import CaseControllerV2, CaseControllerV3
from app.controller.file_controller import FileController
from app.service.task_service import get_task_status, get_tasks_status, submit_case_history
from app.schema.schema import BulkSubmitRequest, BulkTaskStatusRequest
from typing import List, Dict, Any, Optional
from fastapi.responses import JSONResponse
from fastapi import APIRouter, UploadFile, File, Form, Body

case_controller_v2 = CaseControllerV2()
case_controller_v3 = CaseControllerV3()
file_controller = FileController()

def create_case_route() -> APIRouter:
    router = APIRouter(
        prefix="/case"
    )


    @router.get("/{tenant_id}")
    async def get_all_cases(tenant_id: str):
        try:
            result = await case_controller_v3.get_all_cases(tenant_id)
            if result: 
                return JSONResponse({"result": result, "success": True, "count": len(result)}, status_code=200)
            return JSONResponse({"result": result, "success": True, "count": len(result)}, status_code=500)
        
        except Exception as e:
            return JSONResponse({"success": False, "result": [], "error": str(e)}, status_code=500)
        
    
    @router.get("/{tenant_id}/{case_id}")
    async def get_case(tenant_id: str, case_id: str):
        try:
            result = await case_controller_v3.get_case(tenant_id, case_id)
            if result: 
                return JSONResponse({"result": result, "success": True}, status_code=200)
            return JSONResponse({"result": result, "success": True}, status_code=500)
        
        except Exception as e:
            return JSONResponse({"success": False, "result": {}, "error": str(e)}, status_code=500)


    @router.post("/")
    async def create_new_case(
        tenant_id: str,
        case_name: str,
        files: List[UploadFile] = File(None),
    ):
        try:
            result = await case_controller_v3.create_new_case(
                tenant_id=tenant_id,
                case_name=case_name,
                files=files
            )

            if result: 
                return JSONResponse({"success": True}, status_code=200)
            
            return JSONResponse({"success": False, "error": "Error create_new_case route"}, status_code=500)
        
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        

    @router.post("/{tenant_id}/{case_id}/files")
    async def upload_files_existed_case(
        tenant_id: str,
        case_name: str,
        files: List[UploadFile],
    ):
        try:
            result = await case_controller_v3.upload_files_existed_case(
                tenant_id=tenant_id,
                case_name=case_name,
                files=files
            )

            if result: 
                return JSONResponse({"success": True}, status_code=200)
            
            return JSONResponse({"success": False, "error": "Error upload_files_existed_case route"}, status_code=500)
        
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        


    # @router.get("/{case_id}/latest-response")
    # async def get_latest_response(case_id: str):
    #     try:
    #         result = await case_controller_v2.get_latest_response(case_id)
    #         if "error" in result:
    #             return JSONResponse({"success": False, "error": result["error"]}, status_code=404)
    #         return JSONResponse({"success": True, "response": result}, status_code=200)
    #     except Exception as e:
    #         return JSONResponse({"success": False, "error": str(e)}, status_code=500)



    @router.post("/submit")
    async def submit_one_case(
        tenant_id: str,
        case_name: str,
        files: List[UploadFile] = None,
        case_id: Optional[str] = None
    ):
        try:
            result, case_id = await case_controller_v3.submit_one_case(
                tenant_id=tenant_id,
                case_id=case_id,
                case_name=case_name,
                files=files)
            return JSONResponse({"case_id": case_id,"success": True, "result": result}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    # @router.post("/v2/submit/bulk", status_code=202)
    # async def submit_bulk_v2(req: BulkSubmitRequest):
    #     """
    #     Body: { "case_ids": ["id1","id2",...] }
    #     Enqueues in-process background jobs and returns their IDs.
    #     """
    #     case_ids = req.case_ids
    #     if not case_ids:
    #         return JSONResponse({"success": False, "error": "case_ids required"}, status_code=400)

    #     accepted = []
    #     for cid in case_ids:
    #         task_id = submit_case_history(str(cid))
    #         accepted.append({"case_id": str(cid), "task_id": task_id})
    #     return JSONResponse({"success": True, "accepted": accepted}, status_code=202)


    # @router.post("/tasks/status")
    # async def get_many_task_status(payload: BulkTaskStatusRequest):
    #     """
    #     Body: { "task_ids": ["...", "..."] }
    #     """
    #     task_ids = payload.task_ids
    #     if not task_ids:
    #         return JSONResponse({"success": False, "error": "task_ids required"}, status_code=400)
    #     return {"results": get_tasks_status(task_ids)}


    @router.patch("/{case_id}")
    async def update_claim_name(case_id: str, new_name: str):
        try:
            res = await case_controller_v3.update_claim_name(case_id, new_name)
            if not res:
                return JSONResponse({"success": False, "error": "update_claim_name"}, status_code=500) 

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
            
            res = await case_controller_v3.remove_files(file_ids)
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
            res = await case_controller_v3.remove_case(case_id)
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

    # @router.delete("/responses/{file_id}")
    # async def delete_response_file(file_id: str):
    #     """Delete a response file record"""
    #     try:
    #         result = await file_controller.remove_response(file_id)
    #         if not result:
    #             return JSONResponse(
    #                 {"success": False, "error": "Failed to delete response file"}, 
    #                 status_code=500
    #             )

    #         return JSONResponse({"success": True, "message": "Response file deleted successfully"}, status_code=200)
    #     except Exception as e:
    #         return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    

    '''
    # TODO:
    - File & Response connection
    - Duplicate files
    - Soft code the status
    '''


    return router
