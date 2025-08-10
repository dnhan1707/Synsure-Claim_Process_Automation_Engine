from fastapi import APIRouter, UploadFile, File, Form, Body
from app.controller.case_controller import CaseControllerV2
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from app.tasks.case_tasks import process_case_history
from app.service.task_service import get_task_status, get_tasks_status
from pydantic import BaseModel

case_controller_v2 = CaseControllerV2()

class BulkSubmitRequest(BaseModel):
    case_ids: List[str]

def create_case_route() -> APIRouter:
    router = APIRouter(
        prefix="/case"
    )


    @router.get("/")
    async def get_all_cases():
        try:
            result = await case_controller_v2.get_cases()

            if result: 
                return JSONResponse({"result": result}, status_code=200)
            return JSONResponse({"success": False}, status_code=500)
        
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    @router.get("/{case_id}")
    async def case_data(case_id: str):
        try:
            files = await case_controller_v2.get_case_files_links_supabase(case_id=case_id)
            return JSONResponse({"files": files}, status_code=200)
        except Exception as e:
            return JSONResponse({"files": [], "error": str(e)}, status_code=500)


    @router.get("/{case_id}/latest-response")
    async def get_latest_response(case_id: str):
        try:
            result = await case_controller_v2.get_latest_response(case_id)
            if "error" in result:
                return JSONResponse({"success": False, "error": result["error"]}, status_code=404)
            return JSONResponse({"success": True, "response": result}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    @router.post("/save")
    async def save_case(
        case_id: str = Form(None),
        case_name: str = Form(...),
        manual_input: str = Form(None),
        files: List[UploadFile] = File(None),
    ):
        try:
            result = await case_controller_v2.create_case(
                case_id=case_id,
                case_name=case_name,
                manual_inputs=manual_input,
                files=files
            )

            if result.get("success"): 
                return JSONResponse({"success": True}, status_code=200)
            
            return JSONResponse({"success": False, "error": result.get("error", "Unknown error")}, status_code=500)
        
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    @router.post("/submit")
    async def submit_one_case(
        case_id: str = Form(None),
        case_name: str = Form(None),
        manual_input: str = Form(None),
        files: List[UploadFile] = File(None),
    ):
        try:
            result, case_id = await case_controller_v2.submit_one_case(
                case_id=case_id,
                case_name=case_name,
                manual_input=manual_input,
                files=files)
            return JSONResponse({"case_id": case_id,"success": True, "result": result}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    @router.post("/submit/bulk")
    async def submit_bulk(case_ids: List[str]):
        try:
            result = await case_controller_v2.submit_bulk(case_ids=case_ids)
            if result.get("success"): 
                return JSONResponse({"success": True}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    @router.post("/v2/submit/bulk", status_code=202)
    async def submit_bulk_v2(req: BulkSubmitRequest):
        """
        Body: { "case_ids": ["id1","id2",...]}
        Enqueues one Celery task per case_id and returns their IDs.
        """
        case_ids = req.case_ids
        if not case_ids:
            return JSONResponse({"success": False, "error": "case_ids required"}, status_code=400)

        accepted = []
        for cid in case_ids:
            task = process_case_history.delay(str(cid))
            accepted.append({"case_id": str(cid), "task_id": task.id})
        return JSONResponse({"success": True, "accepted": accepted}, status_code=202)


    @router.get("/tasks/{task_id}")
    async def get_celery_task(task_id: str):
        return get_task_status(task_id)


    @router.post("/tasks/status")
    async def get_many_task_status(payload: Dict[str, Any] = Body(...)):
        """
        Body: { "task_ids": ["...", "..."] }
        """
        task_ids = payload.get("task_ids") or []
        if not isinstance(task_ids, list) or not task_ids:
            return JSONResponse({"success": False, "error": "task_ids required"}, status_code=400)
        return {"results": get_tasks_status(task_ids)}


    @router.put("/")
    async def update_case(
        case_id: str = Form(...),
        case_name: str = Form(...),
    ):
        try:
            result = await case_controller_v2.update_case(
                case_id=case_id,
                new_case_name=case_name
            )

            if result.get("success"): 
                return JSONResponse({"success": True}, status_code=200)
            
            return JSONResponse({"success": False, "error": result.get("error", "Unknown error")}, status_code=500)
        
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    @router.delete("/")
    async def delete_case(case_ids: List[str]):
        try:
            result = await case_controller_v2.delete(case_ids=case_ids)

            # Check if any case was successfully updated
            if "results" in result and any(r.get("success") for r in result["results"]):
                return JSONResponse({"success": True, "results": result["results"]}, status_code=200)
            
            return JSONResponse({"success": False, "results": result.get("results", []), "error": "No cases updated"}, status_code=500)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    
    
    return router
