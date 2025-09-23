from fastapi import UploadFile
from typing import Optional
from app.service.supabase_service import SupabaseService
from app.config.settings import get_settings
from app.service.s3_service import FileService
import logging
import uuid

logger = logging.getLogger(__name__)

class FileUploadManager():
    def __init__(self):
        self.file_service = FileService()
        self.sp_service = SupabaseService()

        setting = get_settings()
        s3_setting = setting.s3
        if setting.env and setting.env.lower() == "development":
            self.aws_bucket_name = s3_setting.bucket_name_development or s3_setting.bucket_name
        else: 
            self.aws_bucket_name = s3_setting.bucket_name


    async def upload_normal(self, tenant_id: str, case_id: str, files: list[UploadFile]) -> bool:
        try:
            logger.info("Starting upload_normal: tenant_id=%s, case_id=%s, files_count=%d", 
                    tenant_id, case_id, len(files))
            
            if not files:
                logger.warning("No files to upload")
                return True  
            
            # Upload to S3
            logger.info("Uploading %d files to S3...", len(files))
            s3_result = await self.file_service.save_files(tenant_id, files, case_id)
            
            if not s3_result.get("success", False):
                return False
            
            # Check if s3_result has the expected format
            if not isinstance(s3_result["s3_keys"], list):
                logger.error("S3 upload failed - unexpected response format: %s", type(s3_result))
                return False
            
            if len(s3_result["s3_keys"]) == 0:
                logger.error("S3 upload failed - no files uploaded")
                return False
            
            
            # Prepare data for database
            data_to_insert = []
            for i, s3_key_info in enumerate(s3_result["s3_keys"]):
                try:
                    # Validate tuple format
                    if not isinstance(s3_key_info, tuple):
                        return False
                    
                    s3_key = s3_key_info[0]
                    file_name = s3_key_info[1]
                    
                    if not s3_key or not file_name:
                        logger.error("Missing s3_key or filename at index %d: %s", i, s3_key_info)
                        return False
                    
                    data_to_insert.append({
                        "tenant_id": tenant_id,
                        "case_id": case_id,
                        "kind": "raw_upload",
                        "name": file_name,
                        "s3_bucket": self.aws_bucket_name,
                        "s3_key": s3_key
                    })
                    
                    logger.debug("Prepared file record: %s -> %s", file_name, s3_key)
                    
                except Exception as parse_error:
                    logger.error("Error parsing S3 result at index %d: %s - %s", 
                            i, s3_key_info, str(parse_error))
                    return False

            logger.info("Prepared %d records for database insertion", len(data_to_insert))
            
            # Insert into Supabase
            logger.info("Inserting files into database...")
            sp_response = await self.sp_service.insert_bulk(
                table_name="files",
                objects=data_to_insert
            )

            # Validate database response
            if sp_response is None:
                logger.error("Database insert failed - returned None")
                return False
            
            if not isinstance(sp_response, list):
                logger.error("Database insert failed - unexpected response type: %s", type(sp_response))
                return False
            
            if len(sp_response) != len(data_to_insert):
                logger.error("Database insert partial failure - expected %d, got %d records", 
                        len(data_to_insert), len(sp_response))
                return False
            
            logger.info("Successfully uploaded and saved %d files", len(sp_response))
            return True
            
        except Exception as e:
            logger.error("Error in upload_normal: tenant_id=%s, case_id=%s - %s", 
                        tenant_id, case_id, str(e), exc_info=True)
            return False
        

    async def upload_keep_both(self, tenant_id: str, case_id: str, file: UploadFile) -> bool:
        try:
            logger.info("Starting upload_keep_both for file: %s", file.filename)
            
            count_res = await self.sp_service.count_file(tenant_id, case_id, file.filename)

            if count_res < 0:
                logger.error("Error with count_file since count_res < 0")
                return False

            elif count_res == 0:
                logger.error("No duplicates found but upload_keep_both was called - this shouldn't happen")
                return False

            else:
                base_name, extension = self._split_filename(file.filename)
                resolved_name = f"{base_name} ({count_res}){extension}"
                
                new_s3_key = f"{tenant_id}/{case_id}/uploads/{resolved_name}"
                
                logger.info("Uploading with resolved name: %s -> %s", file.filename, resolved_name)
                
                s3_response = await self.file_service.save_one_file_with_assigned_key(file, new_s3_key)
                
                if not s3_response:
                    logger.error("Error uploading into S3")
                    return False
                
                # upload to supabase
                sp_response = await self.sp_service.insert(
                    table_name="files",
                    object={
                        "tenant_id": tenant_id,
                        "case_id": case_id,
                        "kind": "raw_upload",
                        "name": resolved_name,  
                        "s3_bucket": self.aws_bucket_name,
                        "s3_key": new_s3_key
                    }
                )

                if not sp_response:
                    logger.error("Error saving to database")
                    return False
                
                logger.info("Successfully uploaded file with resolved name: %s", resolved_name)
                return True

        except Exception as e:
            logger.error("Error with upload_keep_both: %s", str(e), exc_info=True)
            return False

    async def upload_overwrite(self, tenant_id: str, case_id: str, file: UploadFile, target_file_id: str = None) -> bool:
        try:
            logger.info("Starting upload_overwrite for file: %s", file.filename)
            
            # Step 1: Find the existing file to overwrite
            if target_file_id:
                # If specific file ID provided, use it
                existing_file = await self.sp_service.get_row_by_id(
                    id=target_file_id,
                    table_name="files",
                    columns="id, name, s3_key, s3_bucket, tenant_id, case_id"
                )
            else:
                # Find by filename (get the first/latest one)
                existing_files = await self.sp_service.get_files_by_name(
                    tenant_id=tenant_id,
                    case_id=case_id,
                    filename=file.filename
                )
                existing_file = existing_files[0] if existing_files else None
            
            if not existing_file:
                logger.error("No existing file found to overwrite for: %s", file.filename)
                return False
            
            # Validate ownership
            if existing_file["tenant_id"] != tenant_id or existing_file["case_id"] != case_id:
                logger.error("Permission denied: file belongs to different tenant/case")
                return False
            
            logger.info("Found existing file to overwrite: %s (ID: %s)", 
                    existing_file["name"], existing_file["id"])
            
            # Step 2: Upload new file to S3 using the SAME S3 key (this overwrites)
            existing_s3_key = existing_file["s3_key"]
            logger.info("Overwriting S3 object: %s", existing_s3_key)
            
            s3_response = await self.file_service.save_one_file_with_assigned_key(file, existing_s3_key)
            
            if not s3_response:
                logger.error("Failed to upload file to S3")
                return False
            
            logger.info("Successfully overwritten S3 object: %s", existing_s3_key)
            
            # Step 3: Update database record with new metadata
            update_data = {
                "name": file.filename,  # Update filename in case it changed
                "uploaded_at": "now()",  # Update timestamp
                # Keep same s3_key, s3_bucket, tenant_id, case_id
            }
            
            sp_response = await self.sp_service.update(
                table_name="files",
                id=existing_file["id"],
                objects=update_data
            )
            
            if not sp_response:
                logger.error("Failed to update file metadata in database")
                # Note: S3 file is already overwritten at this point
                return False
            
            logger.info("Successfully overwritten file: %s (ID: %s)", file.filename, existing_file["id"])
            return True
            
        except Exception as e:
            logger.error("Error in upload_overwrite for file %s: %s", 
                        file.filename if file else "unknown", str(e), exc_info=True)
            return False


    def _split_filename(self, filename: str) -> tuple[str, str]:
        """Split filename into base name and extension."""
        if '.' in filename:
            parts = filename.rsplit('.', 1)  # Split from right to handle names like "file.backup.txt"
            return parts[0], '.' + parts[1]
        else:
            return filename, ''
            

    

