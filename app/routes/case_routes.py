from fastapi import APIRouter, UploadFile, File, Form
from app.controller.case_controller import CaseController
from fastapi.responses import JSONResponse
from typing import List

case_controller = CaseController()

def create_case_route() -> APIRouter:
    router = APIRouter(
        prefix="/case"
    )

    @router.get("/")
    async def list_cases():
        try:
            result = await case_controller.list_cases()
            return JSONResponse({"result": result}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    @router.get("/{id}")
    async def case_data(id: str):
        try:
            files = await case_controller.get_case_files_links(id)
            return JSONResponse({"files": files}, status_code=200)
        except Exception as e:
            return JSONResponse({"files": [], "error": str(e)}, status_code=500)

    @router.post("/submit")
    async def submit_one_case(
        case_id: str = Form(None),
        case_name: str = Form(None),
        manual_input: str = Form(None),
        files: List[UploadFile] = File(None),
    ):
        try:
            result = await case_controller.handle_submit_one_case(case_id, case_name, manual_input, files)
            if "error" in result:
                return JSONResponse({"success": False, "error": result["error"]}, status_code=result.get("status_code", 500))
            return JSONResponse({"result": result["result"]}, status_code=result.get("status_code", 200))
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    @router.post("/submit/bulk")
    async def submit_bulk_case(
        case_ids: List[str]
    ):
        try:
            results = await case_controller.handle_submit_bulk_case(case_ids)
            return JSONResponse({"success": True, "results": results}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    @router.post("/save")
    async def save_case(
        case_id: str = Form(None),
        case_name: str = Form(None),
        manual_input: str = Form(None),
        files: List[UploadFile] = File(None),
    ):
        try:
            result = await case_controller.save_case(case_id, case_name, files, manual_input)
            if isinstance(result, dict) and result.get("error"):
                return JSONResponse({"success": False, "error": result["error"]}, status_code=result.get("status_code", 400))
            return JSONResponse({"success": True, "case_id": result.get("case_id")}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    

    @router.delete("/")
    async def delete_case(case_ids: List[str]):
        try:
            result = await case_controller.delete_case(case_ids)
            if "error" in result:
                return JSONResponse({"success": False, "error": result["error"]}, status_code=500)
            return JSONResponse({"success": True}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    @router.put("/")
    async def update(
        case_id: str = Form(...),
        case_name: str = Form(...)
    ):
        try:
            result = await case_controller.update(case_id, case_name)
            if not result or ("error" in result):
                return JSONResponse({"success": False, "error": result.get("error", "Unknown error") if result else "Unknown error"}, status_code=500)
            return JSONResponse({"success": True}, status_code=200)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    return router
    