from fastapi import APIRouter, UploadFile, File, Form
from app.controller.case_controller_v2 import CaseControllerV2
from fastapi.responses import JSONResponse
from typing import List

case_controller_v2 = CaseControllerV2()

def create_case_route_v2() -> APIRouter:
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


    @router.post("/submit")
    async def submit_one_case(
        case_id: str = Form(None),
        case_name: str = Form(None),
        manual_input: str = Form(None),
        files: List[UploadFile] = File(None),
    ):
        try:
            result = await case_controller_v2.submit_one_case(
                case_id=case_id,
                case_name=case_name,
                manual_input=manual_input,
                files=files)
            return JSONResponse({"success": True, "result": result}, status_code=200)
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


    @router.post("/save")
    async def create_case(
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
