from app.service.supabase_service import SupabaseServiceV2
from app.service.model_service import ModelService
from app.service.s3_service_v2 import S3Service
from fastapi import UploadFile
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class CaseService:
    def __init__(self):
        self.sp_service = SupabaseServiceV2()
        self.s3_service = S3Service()

    
    async def get_all_cases_by_tenant(self, tenant_id: str) -> list:
        try:
            res = await self.sp_service.get_all_cases_by_tenant(
                table_name="cases",
                tenant_id=tenant_id,
                columns="id, case_name, created_at, updated_at"
            )

            if not res:
                return None
            
            return res

        except Exception as e:
            logger.error(f"Error get_all_cases_by_tenant: {e}")
            return None
        
    
    async def get_case(self, tenant_id: str, case_id: str) -> dict:
        try:
            general_data = await self.sp_service.get_case(
                table_name="cases",
                columns="case_name, created_at, updated_at",
                tenant_id=tenant_id,
                case_id=case_id
            )

            if not general_data:
                return None
            
            s3_key_data = await self.sp_service.get_s3_keys(
                table_name="files",
                columns="name, s3_key, uploaded_at",
                tenant_id=tenant_id,
                case_id=case_id
            )

            presigned_urls = []
            for data in s3_key_data:
                s3_key = data["s3_key"]
                url = await self.s3_service.generate_accessible_link(s3_key)
                presigned_urls.append({
                    "name": data["name"],
                    "url": url,
                    "uploaded_at": data["uploaded_at"]
                })
            
            general_data["presigned_urls"] = presigned_urls

            return general_data


        except Exception as e:
            logger.error(f"Error get_all_cases_by_tenant: {e}")
            return None


    async def create_new_case(self, tenant_id: str, case_name: str, files: list[UploadFile]):
        try:
            # save in table cases
            cases_table_response = await self.sp_service.insert_one(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "case_name": case_name,
                    "status": "open"
                }
            )
            new_case_id = cases_table_response["id"]

            if files:
                saved_files_id = []
                # save in table files and save in s3 at once
                for file in files:
                    filename = file.filename
                    s3_key = f"{tenant_id}/{new_case_id}/uploads/{filename}"
                    response = await self.s3_service.save_with_key(file, s3_key)
                    if not response:
                        logger.error("error save_with_key while create_new_case")
                        return ""

                    files_table_response = await self.sp_service.insert_one(
                        table_name="files",
                        object={
                            "tenant_id": tenant_id,
                            "case_id": new_case_id,
                            "name": filename,
                            "s3_key": s3_key,
                            "s3_bucket": "synsure-test-s3",
                            "kind": "raw_upload"
                        }
                    )
                    if not files_table_response:
                        logger.error("error insert_one while create_new_case")
                        return ""
                    
                    saved_files_id.append(files_table_response["id"])
            
            return (new_case_id, saved_files_id)


        except Exception as e:
            return ""

    async def submit_one(
        self,
        tenant_id: str, 
        case_id: Optional[str], 
        case_name: str, 
        files: list[UploadFile]    
    ) -> tuple:
        try:
            if not case_id: # this is new case
                file_contents = []

                for file in files:
                    content = await file.read()
                    file_contents.append({"filename": file.filename, "content": content})

                model_service = ModelService()
                model_response = await model_service.generate_response_v2(
                    file_contents=file_contents
                )

                if not isinstance(model_response, dict):
                    logger.error("Error model_response is not dict")
                    return {}
                
                new_case_id = await self.create_new_case(tenant_id, case_name, files)

                return (new_case_id, model_response)


        except Exception as e:
            logger.error("Error submit_one")
            return ("", {})


    async def get_latest_response(self, tenant_id: str, case_id: str):
        try:
            response_row = await self.sp_service.get_latest_response(tenant_id, case_id)
            s3_key = response_row["s3_key"]
            response_data = await self.s3_service.get_response_file_data(s3_key)

            if not response_data:
                logger.error(f"Failed to retrieve response data from S3 key: {s3_key}")
                return {}
            
            return response_data

        except Exception as e:
            logger.error("Error get_latest_response")
            return {}

