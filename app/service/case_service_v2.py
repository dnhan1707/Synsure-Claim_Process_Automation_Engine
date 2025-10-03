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
                columns="id, case_name, short_des, created_at, updated_at"
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
                columns="case_name, short_des, created_at, updated_at",
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


    async def create_new_case(self, tenant_id: str, case_name: str, case_type: str, files: list[UploadFile], status: str, short_des: str = "unknown"):
        try:
            # save in table cases
            cases_table_response = await self.sp_service.insert_one(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "case_name": case_name,
                    "status": status,
                    "case_type": case_type,
                    "short_des": short_des 
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
            logger.error("Error create new case")
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


    async def delete_case(self, tenant_id: str, case_id: str):
        """
        Delete a case and all its related data (soft delete by default).
        
        Args:
            tenant_id (str): Tenant ID
            case_id (str): Case ID to delete
            
        Returns:
            dict: Success status and details of what was deleted
        """
        try:
            logger.info(f"Starting case deletion for tenant {tenant_id}, case {case_id}")
            
            # Step 1: Get all S3 keys that need to be deleted (files + responses)
            s3_keys_to_delete = []
            
            # Get file S3 keys
            file_records = await self.sp_service.get_s3_keys(
                table_name="files",
                columns="s3_key",
                tenant_id=tenant_id,
                case_id=case_id
            )
            
            if file_records:
                s3_keys_to_delete.extend([record["s3_key"] for record in file_records if record.get("s3_key")])
            
            # Get response S3 keys  
            response_records = await self.sp_service.get_s3_keys(
                table_name="responses",
                columns="s3_key",
                tenant_id=tenant_id,
                case_id=case_id
            )
            
            if response_records:
                s3_keys_to_delete.extend([record["s3_key"] for record in response_records if record.get("s3_key")])
            
            # Step 2: Get response IDs for deleting response_input_files
            deleted_response_ids = []
            if response_records:
                # First get all response IDs before soft deleting
                full_response_records = await self.sp_service.get_s3_keys(
                    table_name="responses",
                    columns="id",
                    tenant_id=tenant_id,
                    case_id=case_id
                )
                if full_response_records:
                    deleted_response_ids = [record["id"] for record in full_response_records]
            
            # Step 3: Delete from S3 (if there are files to delete)
            s3_deletion_success = True
            if s3_keys_to_delete:
                logger.info(f"Deleting {len(s3_keys_to_delete)} S3 objects")
                s3_deletion_success = await self.s3_service.delete(s3_keys_to_delete)
                if not s3_deletion_success:
                    logger.warning("S3 deletion failed, but continuing with database cleanup")
            
            # Step 4: Soft delete database records in proper order
            deletion_results = {
                "s3_files_deleted": len(s3_keys_to_delete) if s3_deletion_success else 0,
                "s3_deletion_success": s3_deletion_success
            }
            
            # Delete response_input_files (by response_id)
            response_input_files_deleted = []
            for response_id in deleted_response_ids:
                deleted_ids = await self._delete_response_input_files_by_response_id(response_id)
                response_input_files_deleted.extend(deleted_ids)
            
            deletion_results["response_input_files_deleted"] = len(response_input_files_deleted)
            
            # Delete tasks
            deleted_task_ids = await self.sp_service.delete_by_tenant_id_case_id(
                table_name="task",
                tenant_id=tenant_id,
                case_id=case_id,
                soft_delete=True
            )
            deletion_results["tasks_deleted"] = len(deleted_task_ids)
            
            # Delete responses  
            deleted_response_ids_db = await self.sp_service.delete_by_tenant_id_case_id(
                table_name="responses",
                tenant_id=tenant_id,
                case_id=case_id,
                soft_delete=True
            )
            deletion_results["responses_deleted"] = len(deleted_response_ids_db)
            
            # Delete files
            deleted_file_ids = await self.sp_service.delete_by_tenant_id_case_id(
                table_name="files",
                tenant_id=tenant_id,
                case_id=case_id,
                soft_delete=True
            )
            deletion_results["files_deleted"] = len(deleted_file_ids)
            
            # Delete case (last)
            deleted_case_ids = await self.sp_service.delete_by_tenant_id_case_id(
                table_name="cases",
                tenant_id=tenant_id,
                case_id=case_id,
                soft_delete=True
            )
            deletion_results["cases_deleted"] = len(deleted_case_ids)
            
            logger.info(f"Case deletion completed: {deletion_results}")
            
            return {
                "success": True,
                "message": "Case deleted successfully",
                "details": deletion_results
            }

        except Exception as e:
            logger.error(f"Error delete_case: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "details": {}
            }

    async def _delete_response_input_files_by_response_id(self, response_id: str):
        """Helper method to delete response_input_files by response_id."""
        try:
            response = await self.sp_service.sp_client.table("response_input_files")\
                .update({"deleted_at": "now()"})\
                .eq("response_id", response_id)\
                .is_("deleted_at", "null")\
                .execute()
                
            if response.data:
                deleted_ids = [record["id"] for record in response.data]
                logger.info(f"Soft deleted {len(deleted_ids)} response_input_files for response {response_id}")
                return deleted_ids
            return []
            
        except Exception as e:
            logger.error(f"Error deleting response_input_files for response {response_id}: {e}")
            return []
        

    async def get_most_case_type_by_tenant(self, tenant_id: str) -> str:
        try:
            response = await self.sp_service.get_by_tenant_id(
                table_name="cases", 
                tenant_id=tenant_id, 
                column="case_type"
            )
            
            if not response:
                return ""
            
            from collections import Counter
            
            case_types = [
                record["case_type"] 
                for record in response 
                if record.get("case_type")  
            ]
            
            if not case_types:
                return ""
            
            counter = Counter(case_types)
            most_common = counter.most_common(1)
            
            return most_common[0][0] if most_common else ""

        except Exception as e:
            logger.error(f"Error get_most_case_type_by_tenant: {e}", exc_info=True)
            return ""


    async def get_most_case_type_general(self) -> str:
        try:
            response = await self.sp_service.get_most_case_type_general(
                column="case_type"
            )
            
            if not response:
                return ""
            
            from collections import Counter
            
            case_types = [
                record["case_type"] 
                for record in response 
                if record.get("case_type")  
            ]
            
            if not case_types:
                return ""
            
            counter = Counter(case_types)
            most_common = counter.most_common(1)
            
            return most_common[0][0] if most_common else ""

        except Exception as e:
            logger.error(f"Error get_most_case_type_general: {e}", exc_info=True)
            return ""

