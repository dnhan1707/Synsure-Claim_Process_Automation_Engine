from app.service.supabase_service import SupabaseService
from app.config.settings import get_settings
from app.service.s3_service import FileService
from app.service.model_service import ModelService
from app.schema.schema import CaseStatus
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
import logging
import uuid
import boto3
import io
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

class CaseService:
    def __init__(self):
        self.file_service = FileService()
        self.model_service = ModelService()
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
        
    async def save_manual_input(
        self, 
        manual_inputs: str, 
        case_id: str, 
        case_name: str, 
        response_data_id: Optional[str]
    ) -> Optional[dict]:

        s3_text_result = await self.file_service.create_text_file_and_save(content=manual_inputs, case_id=case_id)
        text_s3_key = s3_text_result.get("s3_key") if isinstance(s3_text_result, dict) else None
        if text_s3_key:
            return {
                "case_id": case_id,
                "case_name": case_name,
                "s3_link": text_s3_key,
                "response_id": response_data_id
            }
        return None


    async def save_uploaded_files(
        self,
        files: List[UploadFile],
        case_id: str,
        tenant_id: str,
        case_name: str,
        response_data_id: Optional[str]
    ) -> List[dict]:
        result = await self.file_service.save_files(tenant_id=tenant_id, files=files, case_id=case_id)
        
        # Add proper null/error checking
        if not isinstance(result, dict) or "s3_keys" not in result:
            return []
        
        s3_keys = result.get("s3_keys")
        if not s3_keys:  
            return []
        
        files_metadata = []
        for s3_key in s3_keys:
            files_metadata.append({
                "case_id": case_id,
                "kind": "raw_upload",
                "tenant_id": tenant_id,
                # "case_name": case_name,
                "s3_bucket": self.aws_bucket_name,
                "s3_link": s3_key[0],
                "name": s3_key[1],
                "response_id": response_data_id
            })
        
        return files_metadata
    
    
    async def save_uploaded_files_from_contents(
        self,
        file_contents: List[Dict[str, Any]],
        tenant_id: str,
        case_id: str,
        case_name: str,
        response_data_id: Optional[str],
    ) -> List[dict]:
        try:
            logger.info("Saving %d files from contents for case %s", len(file_contents), case_id)
            
            result = await self.file_service.save_files_from_bytes(
                tenant_id=tenant_id, 
                items=file_contents, 
                case_id=case_id
            )
            
            # Add proper null/error checking
            if not isinstance(result, dict) or "s3_keys" not in result:
                logger.error("Failed to save files to S3: %s", result)
                return []
            
            s3_keys = result.get("s3_keys")
            if not s3_keys:  
                logger.warning("No S3 keys returned from file service")
                return []
            
            files_metadata = []
            for s3_key, filename in s3_keys:  # Note: s3_key is a tuple (s3_key, filename)
                files_metadata.append({
                    "id": str(uuid.uuid4()),  # Generate unique ID
                    "case_id": case_id,
                    "tenant_id": tenant_id,
                    "kind": "raw_upload",
                    "name": filename,  # Use the filename from tuple
                    "s3_bucket": self.aws_bucket_name,
                    "s3_key": s3_key,  # Use s3_key from tuple
                    "uploaded_at": "now()",  # Or use proper timestamp
                    # Don't include response_id for uploaded files
                })
                
            logger.info("Prepared %d file metadata records", len(files_metadata))
            return files_metadata
            
        except Exception as e:
            logger.error("Error in save_uploaded_files_from_contents: %s", str(e), exc_info=True)
            return []


    async def save_manual_and_files(
        self,
        tenant_id: str,
        case_id: str,
        case_name: str,
        files: Optional[List[UploadFile]],
        response_data_id: Optional[str],
        file_contents: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        try:
            # logger.info("Starting save_manual_and_files: case_id=%s, files_count=%d, file_contents_count=%d", 
                    # case_id, len(files) if files else 0, len(file_contents) if file_contents else 0)
            
            files_to_insert = []

            # Save files using bytes if provided; else fall back to UploadFile flow
            if file_contents:
                logger.info("Processing file contents...")
                uploaded_files = await self.save_uploaded_files_from_contents(
                    file_contents, tenant_id, case_id, case_name, response_data_id
                )
                files_to_insert.extend(uploaded_files)
                logger.info("Processed %d file contents, got %d metadata records", 
                        len(file_contents), len(uploaded_files))
            elif files:
                logger.info("Processing UploadFile objects...")
                uploaded_files = await self.save_uploaded_files(files, case_id, tenant_id, case_name, response_data_id)
                files_to_insert.extend(uploaded_files)
                logger.info("Processed %d UploadFile objects", len(uploaded_files))

            # Bulk insert new files
            if files_to_insert and response_data_id:
                logger.info("Bulk inserting %d files to database...", len(files_to_insert))
                logger.debug("Files to insert: %s", files_to_insert)  # Debug the actual data
                
                inserted_files = await self.sp_service.insert_bulk(table_name="files", objects=files_to_insert)
                logger.info("Bulk insert completed: %s", inserted_files)
                
                # Check if insert was successful
                if not inserted_files:
                    logger.error("Bulk insert returned False/None")
                elif isinstance(inserted_files, dict) and "error" in inserted_files:
                    logger.error("Bulk insert failed: %s", inserted_files)

                # Conduct the response_input_files relationship
                if isinstance(inserted_files, list):
                    await self._create_response_file_relationships(response_data_id, inserted_files)
                else:
                    logger.warning("Unexpected insert_bulk return type: %s", type(inserted_files))
                

            elif files_to_insert and not response_data_id:
                logger.warning("Files to insert but no response_data_id provided")
                # Still insert files without relationship
                inserted_files = await self.sp_service.insert_bulk(table_name="files", objects=files_to_insert)
                logger.info("Files inserted without response relationship")
            else:
                logger.warning("No files to insert")
            
                
        except Exception as e:
            logger.error("Error in save_manual_and_files for case_id %s: %s", case_id, str(e), exc_info=True)
            raise

    async def proceed_with_model(self, tenant_id: str, case_id: str, case_name: str, files: Optional[List[UploadFile]]):
        try:
            # logger.info("Starting proceed_with_model: case_id=%s, files_count=%d", case_id, len(files) if files else 0)
            
            # Read file contents for model processing
            file_contents = await self._read_uploaded_files(files) if files else []
            logger.info("Read %d file contents for model processing", len(file_contents))
            
            # Generate model response
            logger.info("Generating model response...")
            response = await self.model_service.generate_response_v2(file_contents, None)
            logger.info("Model response generated successfully")
            
            # Save model response FIRST and get response ID
            logger.info("Saving model response...")
            response_data_id = await self._save_model_response(tenant_id, response, case_id)
            
            if not response_data_id:
                logger.error("Failed to save model response, cannot proceed with file relationships")
                return response
                
            logger.info("Model response saved with ID: %s", response_data_id)
            
            # Save files to S3 and database with response relationship
            logger.info("Saving files and creating relationships...")
            await self.save_manual_and_files(
                tenant_id=tenant_id,
                case_id=case_id, 
                case_name=case_name,
                files=None,  # Don't pass consumed files
                response_data_id=response_data_id,  # Pass the response ID
                file_contents=file_contents  # Use the file contents we read
            )
            logger.info("Files and relationships saved successfully")
            
            return response
            
        except Exception as e:
            logger.error("Error in proceed_with_model for case_id %s: %s", case_id, str(e), exc_info=True)
            raise

    async def proceed_with_model_history_files(self, tenant_id: str, case_id: str):
        """
        Generate model response using previously uploaded files for a case.
        Uses cached PDF text and aggregates with manual input.
        """
        # Get file metadata from Supabase
        files_metadata = await self.sp_service.get_files_by_case_id(case_id)
        
        if not files_metadata:
            logger.warning("No files found for case_id: %s", case_id)
            return {
                "decision": "REVIEW_REQUIRED",
                "reasoning": "No files found for this case. Please upload documents to proceed with analysis.",
                "confidence": 0,
                "riskScore": "HIGH",
                "flags": ["NO_FILES_FOUND"]
            }
        
        print("Found %d existing files for case %s", len(files_metadata), case_id)
        

        # Aggregate content from existing files
        manual_input, aggregated_details = await self._aggregate_file_contents_from_metadata(files_metadata)
        
        # Generate model response using aggregated content
        combined_input = f"{manual_input}{aggregated_details}"
        response = await self.model_service.generate_response_v2(
            file_contents=[],  # No new files to parse
            manual_input=combined_input
        )
        
        # Save the response
        response_data_id = await self._save_model_response(tenant_id, response, case_id)
        
        # Link existing files to this new response
        if response_data_id:
            await self._link_existing_files_to_response(files_metadata, case_id, response_data_id)
        
        return response


    async def create_new_case(self, tenant_id: str, case_name: str, files: Optional[List[UploadFile]], status: CaseStatus = CaseStatus.open) -> bool:
        try:
            # insert new case
            res = await self.sp_service.insert(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "status": status.value,
                    "case_name": case_name
                }
            )

            if not res:
                logger.warning("Failed to insert case for tenant_id: %s, case_name: %s", tenant_id, case_name)
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


            logger.info("Successfully created empty claim for tenant_id: %s, case_name: %s", tenant_id, case_name)
            return True

        except Exception as e:
            logger.error("Error create_new_case")
            return False


    async def get_case(self, tenant_id: str, id: str) -> Dict[str, Any]:
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


    async def upload_files_existed_case(self, tenant_id: str, case_id: str, files: List[UploadFile]) -> bool:
        try:
            # logger.info("Starting file upload for case_id: %s with %d files", case_id, len(files))
        
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

# -------------------------------------------------------------Helper Function------------------------------------------------------------------

    async def _create_response_file_relationships(self, response_id: str, inserted_files: List[dict]) -> None:
        """
        Create relationships between response and files in the response_input_files table.
        """
        try:
            logger.info("Creating response-file relationships for response %s with %d files", 
                    response_id, len(inserted_files))
            
            # Prepare relationship records
            relationship_records = []
            for file_record in inserted_files:
                file_id = file_record.get("id")
                if file_id:
                    relationship_records.append({
                        "response_id": response_id,
                        "file_id": file_id
                    })
                else:
                    logger.warning("File record missing ID: %s", file_record)
            
            if relationship_records:
                logger.info("Inserting %d response-file relationships", len(relationship_records))
                logger.debug("Relationships to insert: %s", relationship_records)
                
                # Bulk insert the relationships
                result = await self.sp_service.insert_bulk(
                    table_name="response_input_files", 
                    objects=relationship_records
                )
                
                if result:
                    logger.info("Successfully created %d response-file relationships", len(relationship_records))
                else:
                    logger.error("Failed to create response-file relationships")
            else:
                logger.warning("No valid relationship records to insert")
                
        except Exception as e:
            logger.error("Error creating response-file relationships: %s", str(e), exc_info=True)


    async def _read_uploaded_files(self, files: List[UploadFile]) -> List[Dict[str, Any]]:
        """Extract this for easier testing"""
        file_contents = []
        for file in files:
            content = await file.read()
            file_contents.append({"filename": file.filename, "content": content})
        return file_contents
        

    async def _save_model_response(self, tenant_id: str, response: dict, case_id: str) -> Optional[str]:
        """Save model response to S3 and database"""
        try:
            logger.info("Saving model response for case %s", case_id)
            
            # Save response to S3
            response_saved_res = await self.file_service.save_respose_v2(
                tenant_id=tenant_id, 
                response=response, 
                case_id=case_id
            )
            
            if not isinstance(response_saved_res, dict) or "s3_key" not in response_saved_res:
                logger.error("Failed to save response to S3: %s", response_saved_res)
                return None
                
            response_s3_key = response_saved_res.get("s3_key")
            logger.info("Response saved to S3: %s", response_s3_key)
            
            # Prepare data for responses table - match your schema exactly
            response_data = {
                "tenant_id": tenant_id,
                "case_id": case_id,
                "s3_key": response_s3_key,
                "status": "succeeded",  # Required field, change from default "running"
                # Don't include started_at, completed_at, or created_at - let defaults handle them
                # Or explicitly set completed_at since status is "succeeded"
                "completed_at": "now()"
            }
            
            logger.info("Inserting response data: %s", response_data)
            
            # Save to responses table
            response_row = await self.sp_service.insert(
                table_name="responses",
                object=response_data
            )
            
            logger.info("Insert result: %s", response_row)
            
            if not response_row or "id" not in response_row:
                logger.error("Failed to save response to database. Insert returned: %s", response_row)
                return None
                
            response_id = response_row.get("id")
            logger.info("Response saved to database with ID: %s", response_id)
            return response_id
            
        except Exception as e:
            logger.error("Error in _save_model_response: %s", str(e), exc_info=True)
            return None
    

    async def _aggregate_file_contents_from_metadata(self, files_metadata: List[Dict]) -> tuple[str, str]:
        """
        Aggregate manual input and file details from existing files metadata.
        Returns (manual_input, aggregated_details)
        """
        try:
            logger.info("Aggregating content from %d files", len(files_metadata))
            
            manual_input = ""
            aggregated_details = ""
            
            for file_metadata in files_metadata:
                logger.info("Processing file: %s", file_metadata)
                
                s3_key = file_metadata.get("s3_key")
                file_name = file_metadata.get("name", "unknown")
                file_kind = file_metadata.get("kind", "unknown")
                
                if not s3_key:
                    logger.warning("No S3 key found for file: %s", file_metadata)
                    continue
                
                logger.info("Loading content from S3 key: %s", s3_key)
                
                # Load text content from S3
                if file_kind == "manual_input":
                    # This is a manual input text file
                    text_content = await self._load_text_from_s3(s3_key)
                    manual_input += f"\n{text_content}"
                    logger.info("Added manual input content, length: %d", len(text_content))
                elif file_kind == "raw_upload":
                    # This is an uploaded file - we need to extract/parse it
                    # Check if there's already processed text for this file
                    processed_text = await self._get_processed_text_for_file(file_metadata["id"])
                    
                    if processed_text:
                        aggregated_details += f"\n--- Content from {file_name} ---\n{processed_text}\n"
                        logger.info("Added processed text for %s, length: %d", file_name, len(processed_text))
                    else:
                        # If no processed text, try to extract it now
                        logger.info("No processed text found, attempting to extract from %s", file_name)
                        try:
                            # Download and extract text from the file
                            file_content = await self._download_file_from_s3(s3_key)
                            if file_content:
                                # Use your existing text extraction logic
                                extracted_text = await self._extract_text_from_file_content(file_name, file_content)
                                if extracted_text:
                                    aggregated_details += f"\n--- Content from {file_name} ---\n{extracted_text}\n"
                                    logger.info("Extracted and added text for %s, length: %d", file_name, len(extracted_text))
                        except Exception as extract_error:
                            logger.error("Failed to extract text from %s: %s", file_name, str(extract_error))
            
            logger.info("Aggregation complete - manual_input: %d chars, aggregated_details: %d chars", 
                    len(manual_input), len(aggregated_details))
            
            return manual_input.strip(), aggregated_details.strip()
            
        except Exception as e:
            logger.error("Error aggregating file contents: %s", str(e), exc_info=True)
            return "", ""


    async def _load_text_from_s3(self, s3_key: str) -> str:
        """Load text content from S3 key."""
        try:
            logger.info("Loading text from S3 key: %s", s3_key)
            
            s3_obj = self.s3_client.get_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key
            )
            content = s3_obj["Body"].read().decode("utf-8")
            logger.info("Successfully loaded text from S3, length: %d", len(content))
            return content
            
        except Exception as e:
            logger.error("Error loading text from S3 key %s: %s", s3_key, str(e), exc_info=True)
            return ""

    async def _link_existing_files_to_response(self, files_metadata: List[Dict], case_id: str, response_data_id: str) -> None:
        """Link existing files to a new response using the response_input_files junction table."""
        try:
            logger.info("Linking %d existing files to response %s", len(files_metadata), response_data_id)
            
            relationship_records = []
            for file_metadata in files_metadata:
                file_id = file_metadata.get("id")
                if file_id:
                    relationship_records.append({
                        "response_id": response_data_id,
                        "file_id": file_id
                    })
                else:
                    logger.warning("File metadata missing ID: %s", file_metadata)
            
            if relationship_records:
                logger.info("Creating %d file-response relationships", len(relationship_records))
                
                # Use the junction table instead of updating files directly
                result = await self.sp_service.insert_bulk(
                    table_name="response_input_files",
                    objects=relationship_records
                )
                
                if result:
                    logger.info("Successfully linked %d files to response %s", len(relationship_records), response_data_id)
                else:
                    logger.error("Failed to link files to response")
            else:
                logger.warning("No valid files to link to response")
                
        except Exception as e:
            logger.error("Error linking files to response %s: %s", response_data_id, str(e), exc_info=True)

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
                

    async def _download_file_from_s3(self, s3_key: str) -> Optional[bytes]:
        """Download file content from S3."""
        try:
            logger.info("Downloading file from S3: %s", s3_key)
            
            response = self.s3_client.get_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key
            )
            content = response["Body"].read()
            logger.info("Downloaded file, size: %d bytes", len(content))
            return content
            
        except Exception as e:
            logger.error("Error downloading file from S3 %s: %s", s3_key, str(e))
            return None

    async def _get_processed_text_for_file(self, file_id: str) -> Optional[str]:
        """Check if there's already processed text for this file."""
        try:
            # Check if you store processed text somewhere (maybe in another table?)
            # For now, return None to force re-extraction
            return None
            
        except Exception as e:
            logger.error("Error getting processed text for file %s: %s", file_id, str(e))
            return None

    async def _extract_text_from_file_content(self, filename: str, content: bytes) -> Optional[str]:
        """Extract text from file content based on file type."""
        try:
            logger.info("Extracting text from file: %s, size: %d bytes", filename, len(content))
            
            filename_lower = filename.lower()
            
            if filename_lower.endswith('.pdf'):
                # Use your existing PDF extraction logic
                try:
                    
                    pdf_file = io.BytesIO(content)
                    reader = PdfReader(pdf_file)
                    
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    
                    logger.info("Extracted %d characters from PDF: %s", len(text), filename)
                    return text.strip()
                    
                except Exception as pdf_error:
                    logger.error("Failed to extract PDF text from %s: %s", filename, str(pdf_error))
                    return None
                    
            elif filename_lower.endswith(('.txt', '.md', '.csv')):
                try:
                    text = content.decode('utf-8')
                    logger.info("Extracted %d characters from text file: %s", len(text), filename)
                    return text
                except UnicodeDecodeError:
                    try:
                        text = content.decode('latin-1')
                        logger.info("Extracted %d characters from text file (latin-1): %s", len(text), filename)
                        return text
                    except Exception as decode_error:
                        logger.error("Failed to decode text file %s: %s", filename, str(decode_error))
                        return None
                        
            elif filename_lower.endswith(('.doc', '.docx')):
                # Use python-docx for Word documents
                try:
                    from docx import Document
                    import io
                    
                    doc_file = io.BytesIO(content)
                    doc = Document(doc_file)
                    
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    
                    logger.info("Extracted %d characters from Word document: %s", len(text), filename)
                    return text.strip()
                    
                except Exception as doc_error:
                    logger.error("Failed to extract Word document text from %s: %s", filename, str(doc_error))
                    return None
                    
            else:
                logger.warning("Unsupported file type for text extraction: %s", filename)
                return f"[File: {filename} - Content extraction not supported for this file type]"
                
        except Exception as e:
            logger.error("Error extracting text from %s: %s", filename, str(e), exc_info=True)
            return None