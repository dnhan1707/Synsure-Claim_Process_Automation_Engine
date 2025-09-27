from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from app.service.case_service_v2 import CaseService

case_service = CaseService()

def create_case_routes_v2() -> APIRouter:
    router = APIRouter(prefix="/api/v2/case")

    '''
    GET "/{tenant_id}" : get all cases   NOT TESTED
    
    return: List
            {   
                id:
                case_name:
                created_at:
                updated_at:
            }
    '''
    @router.get("/{tenant_id}")
    async def get_all_cases(tenant_id: str):
        try:
            res = await case_service.get_all_cases_by_tenant(tenant_id)

            if not res:
                return JSONResponse({"success": False, "result": []}, status_code=500)

            return JSONResponse({"success": True, "result": res}, status_code=200)


        except Exception as e:
            return JSONResponse({"success": False, "error": str(e), "result": []}, status_code=500)

    '''
    GET "/{tenant_id}/{case_id}": get info of a case    NOT TESTED
    return: Dict
            {
                case_name:
                created_at:
                updated_at:
                presigned_urls: [  (this links to access all files)
                    {name, url, uploaded_at}
                ]
            }
    '''
    @router.get("/{tenant_id}/{case_id}")
    async def get_case(tenant_id: str, case_id: str):
        try:
            res = await case_service.get_case(tenant_id, case_id)

            if not res:
                return JSONResponse({"success": False, "result": {}}, status_code=500)

            return JSONResponse({"success": True, "result": res}, status_code=200)


        except Exception as e:
            return JSONResponse({"success": False, "error": str(e), "result": {}}, status_code=500)
        

    '''
    POST "/": create a new case, and save with/without files
    Body: 
        {
            tenant_id: str
            case_name: str
            files: list[UploadFile] = Form(None)
        }
    return: newly created case Id

    '''
    @router.post("/")
    async def create_new_case(
        tenant_id: str,
        case_name: str,
        files: list[UploadFile] = File(None)
    ):
        try:
            new_case_id, saved_files_id = await case_service.create_new_case(tenant_id, case_name, files)

            if not new_case_id:
                return JSONResponse({"success": False, "new_case_id": ""}, status_code=500)

            return JSONResponse({"success": True, "new_case_id": new_case_id}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
            


    '''
    GET "/latest-response/{tenant_id}/{case_id}": get latest response from our AI model thru the json file
    return: Dict 
            {
                all the field in a response.json file
            }
    '''
    @router.get("/latestresponse/{tenant_id}/{case_id}")
    async def get_latest_response(tenant_id: str, case_id: str):
        try:
            res = await case_service.get_latest_response(tenant_id, case_id)

            if not res:
                return JSONResponse({"success": False, "result": {}}, status_code=500)


            return JSONResponse({"success": True, "result": res}, status_code=200)

        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)


    return router
