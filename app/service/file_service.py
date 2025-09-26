from fastapi import UploadFile
from app.service.supabase_service import SupabaseServiceV2
from app.service.s3_service_v2 import S3Service
import logging
import os


logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.sp_service = SupabaseServiceV2()
        self.s3_service = S3Service()

    async def check_duplicate_files(
        self,
        tenant_id: str,
        case_id: str,
        files: list[UploadFile]
    ) -> dict:
        '''
        return {
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

        }
        '''
        try:
            # we mainly check by files' names
            duplicate_map = {}
            for new_file in files:
                new_file_name = new_file.filename
                files_found = await self.sp_service.find_duplicates_by_filename(
                    table_name="files",
                    tenant_id=tenant_id,
                    case_id=case_id,
                    target_filename=new_file_name,
                    columns="id, name, s3_key, uploaded_at"
                )
                
                if len(files_found) > 0:
                    duplicate_map[new_file_name] = files_found
                    '''
                    example of how it would look like:

                    {
                        file_1 : [
                            {id, name, s3_key, uploaded_at}
                        ]
                    }
                    '''
                
            if duplicate_map:
                return {
                    "success": True,
                    "has_dup": True,
                    "duplicates": duplicate_map
                }

            else:
                return {
                    "success": True,
                    "has_dup": False,
                    "duplicates": {}
                }

        except Exception as e:
            logger.error("Error in check_duplicate_files")
            return {"success": False}
    

    async def upload_files(
        self,
        tenant_id: str,
        case_id: str,
        files: list[UploadFile],
        file_actions: list[dict]  # [{target_id: str, action: str(upload|overwrite|keep)}]
    ) -> bool:
        try:
            for idx, file in enumerate(files):
                file_action = file_actions[idx]
                target_id = file_action.get("target_id") 
                action = file_action.get("action")

                if action == "upload":
                    response = await self.upload_normal(tenant_id, case_id, file)

                elif action == "overwrite":
                    response = await self.upload_overwrite(tenant_id, case_id, file, target_id)

                elif action == "keep":
                    response = await self.upload_keep(tenant_id, case_id, file)

                else:
                    logger.error(f"Invalid action '{action}' for file index {idx}")
                    return False

                if not response:
                    logger.error(f"Failed to {action} file '{file.filename}'")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error in upload_files: {e}")
            return False

    
    async def upload_normal(self, tenant_id: str, case_id: str, file: UploadFile) -> bool:
        try:
            filename = file.filename
            s3_key = f"{tenant_id}/{case_id}/uploads/{filename}"
            response = await self.s3_service.save_with_key(file, s3_key)
            if not response:
                logger.error("error save_with_key while upload_normal")
                return ""

            files_table_response = await self.sp_service.insert_one(
                table_name="files",
                object={
                    "tenant_id": tenant_id,
                    "case_id": case_id,
                    "name": filename,
                    "s3_key": s3_key,
                    "s3_bucket": "synsure-test-s3",
                    "kind": "raw_upload"
                }
            )
            if not files_table_response:
                logger.error("error insert_one while upload_normal")
                return False
            
            return True

        except Exception as e:
            logger.error(f"Error upload_normal: {e}")
            return False


    async def upload_overwrite(self, tenant_id: str, case_id: str, file: UploadFile, target_id: str) -> bool:
        try:
            '''
            this function is not recommended to be used since this would affect the history tracing
            the response file id still point to the same id but the file is now different
            '''
            file_row = await self.sp_service.get_by_id(
                table_name="files",
                columns="tenant_id, case_id, name, s3_key, uploaded_at",
                id=target_id
            )

            if not file_row:
                logger.error(f"No file row found for id={target_id}")
                return False

            '''
            the supabase still the same, but we would update the s3
            '''
            res = await self.s3_service.overwrite_file(file, file_row["s3_key"])
            return res

        except Exception as e:
            logger.error("Error upload_normal")
            return False


    async def upload_keep(self, tenant_id: str, case_id: str, file: UploadFile) -> bool:
        try:
            filename = file.filename

            files_found = await self.sp_service.find_duplicates_by_filename(
                table_name="files",
                tenant_id=tenant_id,
                case_id=case_id,
                target_filename=filename,
                columns="id, name, s3_key, uploaded_at"
            )

            # handle duplicate naming
            new_filename = filename
            if files_found:
                count = len(files_found)
                name, ext = os.path.splitext(filename)
                new_filename = f"{name} ({count + 1}){ext}"

            # upload to S3
            s3_key = f"{tenant_id}/{case_id}/uploads/{new_filename}"
            response = await self.s3_service.save_with_key(file, s3_key)
            if not response:
                logger.error("error save_with_key while upload_keep")
                return False

            # insert in Supabase
            files_table_response = await self.sp_service.insert_one(
                table_name="files",
                object={
                    "tenant_id": tenant_id,
                    "case_id": case_id,
                    "name": new_filename,
                    "s3_key": s3_key,
                    "s3_bucket": self.s3_service.aws_bucket_name,
                    "kind": "raw_upload"
                }
            )
            if not files_table_response:
                logger.error("error insert_one while upload_keep")
                return False

            return True

        except Exception as e:
            logger.error(f"Error upload_keep: {e}")
            return False

