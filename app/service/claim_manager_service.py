import logging
from app.service.supabase_service import SupabaseService
from app.schema.schema import CaseStatus
from fastapi import UploadFile, File, Form
from typing import List, Dict, Any
import uuid
import boto3
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

class ClaimManagerService:
    def __init__(self):
        self.sp_service = SupabaseService()
        setting = get_settings()
        s3_setting = setting.s3
        self.s3_client = boto3.client(
            service_name=s3_setting.service_name,
            aws_access_key_id=s3_setting.aws_access_key_id,
            aws_secret_access_key=s3_setting.aws_secret_access_key,
            region_name=s3_setting.region_name
        )
        if setting.env and setting.env.lower() == "development":
            self.aws_bucket_name = s3_setting.bucket_name_development or s3_setting.bucket_name
        else: 
            self.aws_bucket_name = s3_setting.bucket_name


    async def create_empty_claim(
        self, 
        tenant_id: str, 
        name: str, 
        status: CaseStatus = CaseStatus.open
    ) -> bool:
        try:
            res = await self.sp_service.insert(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "status": status.value,
                    "case_name": name
                }
            )

            if not res:
                logger.warning("Failed to insert case for tenant_id: %s, case_name: %s", tenant_id, name)
                return False
            
            logger.info("Successfully created empty claim for tenant_id: %s, case_name: %s", tenant_id, name)
            return True

        except Exception as e:
            logger.error("Claim Manager Service Error - create_empty_claim for tenant_id: %s, case_name: %s - %s", 
                        tenant_id, name, str(e), exc_info=True)
            return False
        
    
    async def create_claim(
        self,
        tenant_id: str,
        name: str,
        files: List[UploadFile] = File(None),
        status: CaseStatus = CaseStatus.open
    ) -> bool:
        
        try:
            res = await self.sp_service.insert(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "status": status.value,
                    "case_name": name
                }
            )

            if not res:
                logger.warning("Failed to insert case for tenant_id: %s, case_name: %s", tenant_id, name)
                return False
            
            case_id = res["id"]

            if files:
                for file in files:
                    file_id = str(uuid.uuid4())
                    s3_key = f"{tenant_id}/{case_id}/uploads/{file_id}_{file.filename}"

                    # upload on S3
                    self.s3_client.upload_fileobj(file.file, self.aws_bucket_name, s3_key)

                    # insert into DB
                    insert_res = await self.sp_service.insert(
                        table_name="files",
                        object={
                            "id": file_id,
                            "tenant_id": tenant_id,
                            "case_id": case_id,
                            "kind": "raw_upload",
                            "name": file.filename,
                            "s3_bucket": self.aws_bucket_name,
                            "s3_key": s3_key,
                        }
                    )
                    if not insert_res:
                        logger.warning("No files was inserted")
                        return False

                    logger.info("Uploaded file %s to S3 and inserted into DB", file.filename)


            logger.info("Successfully created empty claim for tenant_id: %s, case_name: %s", tenant_id, name)
            return True

        except Exception as e:
            logger.error("Claim Manager Service Error - create_empty_claim for tenant_id: %s, case_name: %s - %s", 
                        tenant_id, name, str(e), exc_info=True)
            return False
        

    async def get_claim_by_id(self, id: str) -> Dict[str, Any]:
        try:
            general_data = await self.sp_service.get_row_by_id(
                id=id,
                table_name="cases",
                columns="id, tenant_id, case_name, status"
            )
            if not general_data:
                logger.warning("No case found with id: %s", id)
                return {}
            
            tenant_id = general_data["tenant_id"]

            related_files = await self.sp_service.get_all_files(
                table_name="files",
                case_id=id,
                tenant_id=tenant_id,
                columns="id, name, kind, s3_bucket, s3_key, uploaded_at"
            )
            files_with_urls = []
            if related_files:
                for file in related_files:
                    try:
                        presigned_url = self.s3_client.generate_presigned_url(
                            "get_object",
                            Params={
                                "Bucket": file["s3_bucket"],
                                "Key": file["s3_key"]
                            },
                            ExpiresIn=900
                        )
                        files_with_urls.append({
                            "id": file["id"],
                            "name": file["name"],
                            "kind": file["kind"],
                            "uploaded_at": file["uploaded_at"],
                            "download_url": presigned_url
                        })

                    except Exception as e:
                        logger.error("Could not generate presigned URL for file %s: %s", file["id"], str(e))

            return {
                "id": general_data["id"],
                "case_name": general_data["case_name"],
                "status": general_data["status"],
                "files": files_with_urls   
                }   

        except Exception as e:
            logger.error("Error get_claim_by_id")
            return {}


    async def get_all_claim(self) -> List[Dict[str, Any]]:
        try:
            res = await self.sp_service.get_all(
                table_name="cases",
                columns="id, tenant_id, case_name, status"
            )
            if not res:
                logger.error("Error get_all_claim either empty or None")
                return []

            return res

        except Exception as e:
            logger.error("Error get_all_claim")
            return []


    async def update_claim_name(self, id: str, new_name: str) -> bool:
        try:
            res = await self.sp_service.update(
                table_name="cases",
                id=id,
                objects={
                    "case_name": new_name
                }
            )
            if not res:
                return False
            
            return True

        except Exception as e:
            logger.error("Error update_claim_name")
            return False
        
    
    async def upload_files_existed_case(self, tenant_id: str, case_id: str, files: List[UploadFile]) -> bool:
        try:
            logger.info("Starting file upload for case_id: %s with %d files", case_id, len(files))
        
            logger.info("Found case for tenant_id: %s", tenant_id)
            
            # Get existing files for this case to check for name conflicts
            existing_files = await self.sp_service.get_all_files(
                table_name="files",
                case_id=case_id,
                tenant_id=tenant_id,
                columns="name"
            )
            
            existing_file_names = []
            if existing_files:
                existing_file_names = [file["name"] for file in existing_files]
                logger.info("Found %d existing files in case", len(existing_file_names))
            
            uploaded_count = 0
            
            for file in files:
                try:
                    # Generate unique filename if conflict exists
                    final_filename = self._resolve_filename_conflict(file.filename, existing_file_names)
                    
                    if final_filename != file.filename:
                        logger.info("Filename conflict resolved: '%s' -> '%s'", file.filename, final_filename)
                    
                    # Add the new filename to existing names to avoid conflicts within this batch
                    existing_file_names.append(final_filename)
                    
                    file_id = str(uuid.uuid4())
                    s3_key = f"{tenant_id}/{case_id}/uploads/{file_id}_{final_filename}"
                    
                    # Upload to S3
                    logger.info("Uploading file %s to S3", final_filename)
                    self.s3_client.upload_fileobj(file.file, self.aws_bucket_name, s3_key)
                    
                    # Insert into database
                    insert_res = await self.sp_service.insert(
                        table_name="files",
                        object={
                            "id": file_id,
                            "tenant_id": tenant_id,
                            "case_id": case_id,
                            "kind": "raw_upload",
                            "name": final_filename,  # Use the resolved filename
                            "s3_bucket": self.aws_bucket_name,
                            "s3_key": s3_key,
                        }
                    )
                    
                    if not insert_res:
                        logger.error("Failed to insert file %s into database", final_filename)
                        return False
                    
                    logger.info("Successfully uploaded and saved file: %s", final_filename)
                    uploaded_count += 1
                    
                except Exception as file_error:
                    logger.error("Failed to upload file %s: %s", file.filename, str(file_error), exc_info=True)
                    return False  # Fail fast on any file error
            
            logger.info("Successfully uploaded %d files for case_id: %s", uploaded_count, case_id)
            return True
            
        except Exception as e:
            logger.error("Error in upload_files_existed_case for case_id: %s - %s", case_id, str(e), exc_info=True)
            return False


    async def replace_existed_file(self, tenant_id: str, case_id: str, file_id: str, new_file: UploadFile) -> bool:
        try:
            logger.info("Replacing file %s in case %s", file_id, case_id)
            
            # First, get the existing file info
            existing_file = await self.sp_service.get_row_by_id(
                id=file_id,
                table_name="files",
                columns="id, name, s3_bucket, s3_key, tenant_id, case_id"
            )
            
            if not existing_file:
                logger.error("File %s not found", file_id)
                return False
                
            # Verify the file belongs to the correct tenant and case
            if existing_file["tenant_id"] != tenant_id or existing_file["case_id"] != case_id:
                logger.error("File %s does not belong to tenant %s or case %s", file_id, tenant_id, case_id)
                return False
            
            # Get existing files to check for name conflicts (excluding the file being replaced)
            existing_files = await self.sp_service.get_all_files(
                table_name="files",
                case_id=case_id,
                tenant_id=tenant_id,
                columns="id, name"
            )
            
            # Create list of existing names excluding the current file
            existing_file_names = []
            if existing_files:
                existing_file_names = [file["name"] for file in existing_files if file["id"] != file_id]
                logger.info("Found %d other files in case for conflict checking", len(existing_file_names))
            
            # Resolve filename conflicts
            final_filename = self._resolve_filename_conflict(new_file.filename, existing_file_names)
            
            if final_filename != new_file.filename:
                logger.info("Filename conflict resolved: '%s' -> '%s'", new_file.filename, final_filename)
            
            # Generate new S3 key (keeping same file ID to maintain references)
            new_s3_key = f"{tenant_id}/{case_id}/uploads/{file_id}_{final_filename}"
            
            # Upload new file to S3
            logger.info("Uploading replacement file %s to S3", final_filename)
            self.s3_client.upload_fileobj(new_file.file, self.aws_bucket_name, new_s3_key)
            
            # Update database record
            res = await self.sp_service.update( 
                table_name="files",
                id=file_id,
                objects={
                    "name": final_filename,  # Use resolved filename
                    "s3_key": new_s3_key
                }
            )

            if not res:
                logger.error("Failed to update file record in database for file_id: %s", file_id)
                # Clean up the newly uploaded file since DB update failed
                try:
                    self.s3_client.delete_object(Bucket=self.aws_bucket_name, Key=new_s3_key)
                except Exception as cleanup_error:
                    logger.error("Failed to cleanup uploaded file after DB error: %s", str(cleanup_error))
                return False

            # Delete old S3 file after successful update
            try:
                old_s3_key = existing_file["s3_key"]
                self.s3_client.delete_object(Bucket=existing_file["s3_bucket"], Key=old_s3_key)
                logger.info("Successfully deleted old S3 file: %s", old_s3_key)
            except Exception as s3_error:
                # Log but don't fail the operation - the new file is already in place
                logger.warning("Failed to delete old S3 file %s: %s", old_s3_key, str(s3_error))

            logger.info("Successfully replaced file %s with %s", file_id, final_filename)
            return True

        except Exception as e:
            logger.error("Error in replace_existed_file for file_id: %s - %s", file_id, str(e), exc_info=True)
            return False


    def _resolve_filename_conflict(self, original_filename: str, existing_names: List[str]) -> str:
        """
        Resolve filename conflicts by appending (n) where n is the next available number.
        
        Examples:
        - document.pdf -> document (1).pdf -> document (2).pdf
        - image.jpg -> image (1).jpg -> image (2).jpg
        """
        if original_filename not in existing_names:
            return original_filename
        
        # Split filename and extension
        if '.' in original_filename:
            name_part, extension = original_filename.rsplit('.', 1)
            extension = '.' + extension
        else:
            name_part = original_filename
            extension = ''
        
        # Find the next available number
        counter = 1
        while True:
            new_filename = f"{name_part} ({counter}){extension}"
            if new_filename not in existing_names:
                return new_filename
            counter += 1
            
            # Safety check to prevent infinite loop (though unlikely)
            if counter > 1000:
                # Fallback to UUID suffix
                unique_suffix = str(uuid.uuid4())[:8]
                return f"{name_part}_{unique_suffix}{extension}"


    async def remove_files(self, file_ids: List[str]) -> bool:
        """
        Remove multiple files from database and S3
        """
        try:
            logger.info("Service: Removing %d files", len(file_ids))
            
            deleted_count = 0
            
            for file_id in file_ids:
                try:
                    # Get file info first
                    file_info = await self.sp_service.get_row_by_id(
                        id=file_id,
                        table_name="files",
                        columns="id, name, s3_bucket, s3_key"
                    )
                    
                    if not file_info:
                        logger.warning("File %s not found, skipping", file_id)
                        continue
                    
                    # Delete from S3 first
                    try:
                        self.s3_client.delete_object(
                            Bucket=file_info["s3_bucket"], 
                            Key=file_info["s3_key"]
                        )
                        logger.info("Deleted S3 file: %s", file_info["s3_key"])
                    except Exception as s3_error:
                        logger.error("Failed to delete S3 file %s: %s", file_info["s3_key"], str(s3_error))
                        # Continue with DB deletion even if S3 fails
                    
                    # Soft delete in database (recommended)
                    res = await self.sp_service.update(
                        table_name="files",
                        id=file_id,
                        objects={
                            "deleted_at": "now()",
                        }
                    )
                    
                    # OR hard delete (uncomment if you prefer)
                    # res = await self.sp_service.delete(
                    #     table_name="files",
                    #     id=file_id
                    # )
                    
                    if res:
                        deleted_count += 1
                        logger.info("Successfully deleted file: %s (%s)", file_id, file_info["name"])
                    else:
                        logger.error("Failed to delete file from database: %s", file_id)
                        
                except Exception as file_error:
                    logger.error("Error deleting file %s: %s", file_id, str(file_error))
            
            logger.info("Successfully deleted %d out of %d files", deleted_count, len(file_ids))
            return deleted_count > 0  # Return true if at least one file was deleted
            
        except Exception as e:
            logger.error("Error in remove_files: %s", str(e), exc_info=True)
            return False

    async def remove_case(self, case_id: str) -> bool:
        """
        Remove a case and all its associated files
        """
        try:
            logger.info("Service: Removing case %s and all associated files", case_id)
            
            # First, get all files associated with this case
            case_files = await self.sp_service.get_all_files(
                table_name="files",
                case_id=case_id,
                tenant_id="",  # We'll need to modify this method or get tenant_id first
                columns="id, name, s3_bucket, s3_key"
            )
            
            # Alternative: Get case info first to get tenant_id
            case_info = await self.sp_service.get_row_by_id(
                id=case_id,
                table_name="cases",
                columns="id, tenant_id"
            )
            
            if not case_info:
                logger.warning("Case %s not found", case_id)
                return False
            
            # Get files properly with tenant_id
            case_files = await self.sp_service.get_all_files(
                table_name="files",
                case_id=case_id,
                tenant_id=case_info["tenant_id"],
                columns="id, name, s3_bucket, s3_key"
            )
            
            # Delete all associated files first
            if case_files:
                file_ids = [file["id"] for file in case_files]
                logger.info("Found %d files to delete for case %s", len(file_ids), case_id)
                
                files_deleted = await self.remove_files(file_ids)
                if not files_deleted:
                    logger.warning("Failed to delete some files for case %s", case_id)
            
            # Now delete the case itself (soft delete recommended)
            res = await self.sp_service.update(
                table_name="cases",
                id=case_id,
                objects={
                    "deleted_at": "now()",
                }
            )
            
            # OR hard delete (uncomment if you prefer)
            # res = await self.sp_service.delete(
            #     table_name="cases",
            #     id=case_id
            # )
            
            if not res:
                logger.error("Failed to delete case from database: %s", case_id)
                return False
            
            logger.info("Successfully deleted case %s and %d associated files", case_id, len(case_files) if case_files else 0)
            return True
            
        except Exception as e:
            logger.error("Error in remove_case for case_id: %s - %s", case_id, str(e), exc_info=True)
            return False