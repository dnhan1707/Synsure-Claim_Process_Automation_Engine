from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.service.file_service import FileService
import json

file_service = FileService()

def create_file_routes_v2() -> APIRouter:
    router = APIRouter(prefix="/api/v1/file")
    
    '''
    POST "/dupcheck"
    Body: 
        {
            tenant_id: str,
            case_id: str,
            list[UploadFile]
        }
    
    return: 
        {
            success: bool,
            has_dup: bool,
            duplicates: {
                new_file_name: [
                    {
                        id, name, s3_key, uploaded_at
                    },
                    {
                        id, name, s3_key, uploaded_at
                    }
                ]
        }
    '''
    @router.post("/dupcheck")
    async def check_duplicate_files(
        tenant_id: str,
        case_id: str,
        files: list[UploadFile]
    ):
        try:
            res = await file_service.check_duplicate_files(tenant_id, case_id, files)
            if not res["success"]:
                return JSONResponse({"success": False}, status_code=500)

            return JSONResponse(res, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    '''
    POST "/upload" : upload files for a case
    Body: 
        {
            tenant_id: str,
            case_id: str,
            list[UploadFile],
            file_actions: [{target_id: str, action: str(upload, overwrite, keep)}]
        }

        example:
        [
            {
                "target_id": "94df3181-501a-4fd0-a594-3fd3b3b6280e", 
                "action": "overwrite"
            },
            {
                "target_id": "", 
                "action": "keep"
            }
        ]

    return: 
        {
            success: bool   
        }
    '''

    @router.post("/upload")
    async def upload_files(
        tenant_id: str = Form(...),
        case_id: str = Form(...),
        files: list[UploadFile] = File(...),
        file_actions: str = Form(...)
    ):
        try:
            actions = json.loads(file_actions)
            res = await file_service.upload_files(tenant_id, case_id, files, actions)
            if not res:
                return JSONResponse({"success": False}, status_code=500)

            return JSONResponse({"success": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    
    '''
    DELETE
    '''

    return router
