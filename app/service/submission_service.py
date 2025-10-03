from app.service.supabase_service import SupabaseServiceV2
from app.service.model_service import ModelService
from app.service.case_service_v2 import CaseService
from app.service.s3_service_v2 import S3Service
from app.service.model_service import ModelService
from fastapi import UploadFile
import uuid
import logging
import asyncio


logger = logging.getLogger(__name__)

class SubmissionService:
    def __init__(self):
        self.sp_service = SupabaseServiceV2()
        self.s3_service = S3Service()
        self.case_service = CaseService()
        self.model_response = ModelService()

    async def submit_new_case(
        self,
        tenant_id: str, 
        case_name: str, 
        case_type: str,
        files: list[UploadFile]    
    ) -> tuple: # (new_case_id, model_response)
        new_case_id = ""  
        try:
            logger.info(f"Starting submit_new_case for tenant {tenant_id}, case_name: {case_name}")
            
            if not files or len(files) == 0:
                logger.error("No files provided")
                return ("", {})
            
            if not tenant_id or not case_name or not case_type:
                logger.error(f"Missing required fields: tenant_id={tenant_id}, case_name={case_name}, case_type={case_type}")
                return ("", {})

            # Process files
            file_contents = []
            for i, file in enumerate(files):
                try:
                    content = await file.read()
                    if not content:
                        logger.warning(f"File {i} ({file.filename}) is empty")
                        continue
                    file_contents.append({"filename": file.filename, "content": content})
                    logger.info(f"Processed file {i}: {file.filename} ({len(content)} bytes)")
                except Exception as file_error:
                    logger.error(f"Error reading file {i} ({file.filename}): {file_error}")
                    return ("", {})

            if not file_contents:
                logger.error("No valid file contents after processing")
                return ("", {})

            logger.info("Generating AI model response...")
            model_service = ModelService()
            model_response = await model_service.generate_response_v2(file_contents=file_contents)

            if not isinstance(model_response, dict):
                logger.error(f"Invalid model_response type: {type(model_response)}, value: {model_response}")
                return ("", {})
            
            logger.info(f"AI response generated: {model_response}")
            
            short_des = model_response.get("short_des", "")
            
            logger.info("Creating new case...")
            try:
                new_case_id, saved_files_id = await self.case_service.create_new_case(
                    tenant_id=tenant_id,
                    short_des=short_des, 
                    case_name=case_name,
                    case_type=case_type,
                    files=files,
                    status="running"
                )
                
                if not new_case_id:
                    logger.error("create_new_case returned empty case_id")
                    return ("", {})
                    
                if not saved_files_id:
                    logger.error("create_new_case returned empty saved_files_id")
                    await self._update_case_to_failed(new_case_id)
                    return ("", {})
                    
                logger.info(f"Case created successfully: {new_case_id}, files: {saved_files_id}")
                
            except Exception as case_error:
                logger.error(f"Error creating case: {case_error}", exc_info=True)
                return ("", {})

            # Extract rule_used
            rule_used = model_response.get("rule_used", "")
            if isinstance(rule_used, list):
                rule_used = " ".join(rule_used)
            
            # Save response to S3
            logger.info("Saving response to S3...")
            new_response_file_id = str(uuid.uuid4())
            try:
                response_file_key = await self.s3_service.save_response_json(
                    tenant_id, new_case_id, new_response_file_id, model_response
                )
                if not response_file_key:
                    logger.error("S3 save_response_json returned empty key")
                    await self._update_case_to_failed(new_case_id)
                    return ("", {})
                logger.info(f"Response saved to S3: {response_file_key}")
                
            except Exception as s3_error:
                logger.error(f"Error saving to S3: {s3_error}", exc_info=True)
                await self._update_case_to_failed(new_case_id)
                return ("", {})

            # Save to responses table
            logger.info("Saving response to database...")
            try:
                response_row = await self.sp_service.insert_one(
                    table_name="responses",
                    object={
                        "id": new_response_file_id,
                        "tenant_id": tenant_id,
                        "case_id": new_case_id,
                        "s3_key": response_file_key,
                        "status": model_response.get("decision", "unknown"),
                        "rule_used": rule_used
                    }
                )
                
                if not response_row:
                    logger.error("Failed to insert response record")
                    await self._update_case_to_failed(new_case_id)
                    return ("", {})
                logger.info(f"Response record created: {response_row}")
                
            except Exception as db_error:
                logger.error(f"Error saving response to database: {db_error}", exc_info=True)
                await self._update_case_to_failed(new_case_id)
                return ("", {})

            # Save response_input_files relationship
            logger.info("Creating response-file relationships...")
            try:
                rows = []
                for fid in saved_files_id:
                    rows.append({
                        "file_id": fid,
                        "response_id": new_response_file_id
                    })
                
                if rows:
                    insert_bulk_response = await self.sp_service.insert_bulk(
                        table_name="response_input_files",
                        list_object=rows
                    )
                    if not insert_bulk_response:
                        logger.error("Error inserting response_input_files relationships")
                        # Don't fail the whole operation for this
                    else:
                        logger.info(f"Created {len(rows)} response-file relationships")
                
            except Exception as rel_error:
                logger.error(f"Error creating response-file relationships: {rel_error}", exc_info=True)
                # Don't fail the whole operation for this

            # Update case status to final decision
            logger.info("Updating final case status...")
            try:
                if model_response.get("decision"):
                    case_update_result = await self.sp_service.update(
                        table_name="cases",
                        id=new_case_id,
                        object={"status": model_response["decision"]}
                    )
                    if not case_update_result:
                        logger.warning("Failed to update case status, but continuing")
                    else:
                        logger.info(f"Case status updated to: {model_response['decision']}")
                
            except Exception as update_error:
                logger.error(f"Error updating case status: {update_error}", exc_info=True)
                # Don't fail for this
                    
            logger.info(f"submit_new_case completed successfully for case {new_case_id}")
            return (new_case_id, model_response)
            
        except Exception as e:
            logger.error(f"Error in submit_new_case: {e}", exc_info=True) 

            if new_case_id: 
                try:
                    await self._update_case_to_failed(new_case_id)
                except Exception as update_error:
                    logger.error(f"Failed to update case to failed status: {update_error}")
            
            return ("", {})
    

    async def _update_case_to_failed(self, case_id: str):
        """Helper method to update case status to failed."""
        try:
            await self.sp_service.update(
                table_name="cases",
                id=case_id,
                object={"status": "failed"}
            )
        except Exception as e:
            logger.error(f"Failed to update case {case_id} to failed status: {e}")


    async def submit_with_chosen_files(
        self,
        tenant_id: str,
        case_id: str,
        chosen_files: list[str]  # list of file IDs
    ) -> dict:
        try:
            read_data = await self.process_all_files_concurrently(chosen_files)

            if not read_data:
                logger.error("No valid files found in submit_with_chosen_files")
                return {}

            # Update case status to "running"
            await self.sp_service.update(
                table_name="cases",
                id=case_id,
                object={"status": "running"}
            )

            # Generate model response
            model_response = await self.model_response.generate_response_v2(read_data)

            # Validate model response
            if not isinstance(model_response, dict) or "decision" not in model_response:
                logger.error("Invalid model response format")
                
                # Update case status to failed
                await self.sp_service.update(
                    table_name="cases",
                    id=case_id,
                    object={"status": "failed"}
                )
                return {"error": "Invalid model response"}

            # Extract rule_used from model response
            rule_used = model_response.get("rule_used", "")


            # Save into S3
            new_response_file_id = str(uuid.uuid4())
            response_file_key = await self.s3_service.save_response_json(
                tenant_id, case_id, new_response_file_id, model_response
            )
            if not response_file_key:
                logger.error("Error save_response_json in submit_with_chosen_files")
                
                # Update case status to failed
                await self.sp_service.update(
                    table_name="cases",
                    id=case_id,
                    object={"status": "failed"}
                )
                return {}
            
            # Save into responses table with status AND rule_used
            response_insert_result = await self.sp_service.insert_one(
                table_name="responses",
                object={
                    "id": new_response_file_id,
                    "tenant_id": tenant_id,
                    "case_id": case_id,
                    "s3_key": response_file_key,
                    "status": model_response["decision"],
                    "rule_used": rule_used  
                }
            )

            if not response_insert_result:
                logger.error("Failed to insert response record")
                
                # Update case status to failed
                await self.sp_service.update(
                    table_name="cases",
                    id=case_id,
                    object={"status": "failed"}
                )
                return {}

            # Save into response_input_files table
            rows = [{"file_id": fid, "response_id": new_response_file_id} for fid in chosen_files]
            bulk_insert_result = await self.sp_service.insert_bulk(
                table_name="response_input_files", 
                list_object=rows  
            )

            if not bulk_insert_result:
                logger.error("Failed to insert response input files")
                # Don't fail the whole operation for this

            # Update case status to final decision
            short_des = model_response.get("short_des", "")

            # Skip updating short_des only if it's truly empty or None
            if not short_des or short_des.strip() == "":
                # Only update status
                case_status_update = await self.sp_service.update(
                    table_name="cases",
                    id=case_id,
                    object={"status": model_response["decision"]}
                )
            else:
                # Update both status and short_des (including "unknown")
                case_status_update = await self.sp_service.update(
                    table_name="cases",
                    id=case_id,
                    object={
                        "status": model_response["decision"],
                        "short_des": short_des
                    }
                )

            if not case_status_update:
                logger.error("Failed to update case status to final decision")
                # Don't fail the whole operation, but log it

            return model_response

        except Exception as e:
            logger.error(f"Error submit_with_chosen_files: {e}", exc_info=True)
            
            # Update case status to failed on exception
            try:
                await self.sp_service.update(
                    table_name="cases",
                    id=case_id,
                    object={"status": "failed"}
                )
            except Exception as update_error:
                logger.error(f"Failed to update case status to failed: {update_error}")
            
            return {}
        

    async def _process_file(self, file_id: str):
        file_data = await self.sp_service.get_by_id(
            table_name="files",
            columns="name, s3_key",
            id=file_id
        )
        if not file_data:
            logger.warning(f"File not found for id={file_id}")
            return None

        s3_key = file_data["s3_key"]
        raw_content = await self.s3_service.get_file_raw_bytes(s3_key)
        return {
            "filename": file_data["name"],
            "content": raw_content
        }


    async def process_all_files_concurrently(self, chosen_files: list[str]):
        read_data = []

        # process all files concurrently
        results = await asyncio.gather(*[self._process_file(fid) for fid in chosen_files])
        read_data = [r for r in results if r]

        return read_data


    async def submit_many_async(self, tenant_id: str, case_ids: list[str]) -> dict:
        """Submit cases for async processing using task queue."""
        try:
            if not case_ids:
                return {"error": "Empty case_ids list"}
            
            logger.info(f"submit_many_async called with tenant_id={tenant_id}, case_ids={case_ids}")
            
            # Import here to avoid circular imports
            from app.service.task_service_v2 import TaskService
            task_service = TaskService()
            
            # Create task records
            logger.info("Creating batch tasks...")
            task_result = await task_service.create_batch_tasks(tenant_id, case_ids)
            logger.info(f"Task creation result: {task_result}")
            
            if not task_result["success"]:
                return task_result
            
            task_ids = task_result["task_ids"]
            task_id_list = list(task_ids.values())
            
            # Start background processing (don't wait)
            logger.info(f"Starting background processing for task IDs: {task_id_list}")
            asyncio.create_task(self._process_tasks_background(task_id_list))
            
            return {
                "success": True,
                "message": f"Submitted {len(case_ids)} cases for processing",
                "task_ids": task_ids,
                "status_check_info": "Use /task/status/{tenant_id}?task_ids=id1,id2,id3 to check status"
            }
            
        except Exception as e:
            logger.error(f"Error in submit_many_async: {e}", exc_info=True)
            return {"error": str(e)}


    async def _process_tasks_background(self, task_ids: list[str]):
        """Process tasks in background without blocking the response."""
        try:
            logger.info(f"Background processing started for {len(task_ids)} tasks: {task_ids}")
            
            from app.service.task_service_v2 import TaskService
            task_service = TaskService()
            
            # Process up to 3 tasks concurrently to avoid overwhelming the system
            semaphore = asyncio.Semaphore(3)
            
            async def _process_with_semaphore(task_id: str):
                async with semaphore:
                    try:
                        logger.info(f"Starting to process task {task_id}")
                        result = await task_service.process_task(task_id)
                        logger.info(f"Task {task_id} processing result: {result}")
                        return result
                    except Exception as e:
                        logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
                        return {"error": str(e)}
            
            # Process all tasks concurrently
            results = await asyncio.gather(
                *[_process_with_semaphore(tid) for tid in task_ids],
                return_exceptions=True
            )
            
            # Log results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {task_ids[i]} failed with exception: {result}")
                else:
                    logger.info(f"Task {task_ids[i]} completed with result: {result}")
            
            logger.info(f"Completed background processing of {len(task_ids)} tasks")
            
        except Exception as e:
            logger.error(f"Error in background task processing: {e}", exc_info=True)


