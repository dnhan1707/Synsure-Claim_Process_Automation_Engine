from app.service.supabase_service import SupabaseServiceV2
import uuid
import logging

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self):
        self.sp_service = SupabaseServiceV2()
    
    async def create_batch_tasks(self, tenant_id: str, case_ids: list[str]) -> dict:
        """Create tasks for multiple cases and return task IDs."""
        try:
            tasks = []
            task_ids = {}
            
            for case_id in case_ids:
                task_id = str(uuid.uuid4())
                task_ids[case_id] = task_id
                
                tasks.append({
                    "id": task_id,
                    "tenant_id": tenant_id,
                    "case_id": case_id,
                    "status": "queued"
                })
            
            # Insert all tasks at once
            result = await self.sp_service.insert_bulk(
                table_name="task", 
                list_object=tasks 
            )            
            if not result:
                return {"success": False, "error": "Failed to create tasks"}
            
            logger.info(f"Created {len(tasks)} tasks for tenant {tenant_id}")
            return {
                "success": True,
                "task_ids": task_ids,
                "message": f"Created {len(tasks)} tasks"
            }
            
        except Exception as e:
            logger.error(f"Error creating batch tasks: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    

    # In task_service_v2.py - fix process_task method
    async def process_task(self, task_id: str) -> dict:
        """Process a single task."""
        try:
            logger.info(f"Starting to process task {task_id}")
            
            # Get task details
            task = await self.sp_service.get_by_id("task", "*", task_id)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return {"error": "Task not found"}
            
            logger.info(f"Found task: {task}")
            
            # Update status to running 
            await self.sp_service.update_task_status(
                task_id=task_id,
                status="running",
                started_at="now()"
            )
            logger.info(f"Updated task {task_id} status to running")
            
            # Process the case
            tenant_id = task["tenant_id"]
            case_id = task["case_id"]
            
            logger.info(f"Getting files for tenant_id={tenant_id}, case_id={case_id}")
            
            # ✅ Fix: Remove table_name parameter since the method signature doesn't need it
            files = await self.sp_service.get_file_by_case_tenant_id(
                tenant_id=tenant_id,
                case_id=case_id,
                columns="id"
            )
            
            logger.info(f"Found {len(files) if files else 0} files for case {case_id}")
            
            if not files:
                await self.sp_service.update_task_status(
                    task_id=task_id,
                    status="failed",
                    error_message="No files found for case",
                    completed_at="now()"
                )
                logger.warning(f"No files found for case {case_id}")
                return {"error": "No files found"}
            
            file_ids = [f["id"] for f in files]
            logger.info(f"Processing file IDs: {file_ids}")
            
            # Import here to avoid circular imports
            from app.service.submission_service import SubmissionService
            submission_service = SubmissionService()
            
            logger.info(f"Calling submit_with_chosen_files for task {task_id}")
            model_response = await submission_service.submit_with_chosen_files(
                tenant_id, case_id, file_ids
            )
            
            logger.info(f"Model response for task {task_id}: {type(model_response)} - {model_response}")
            
            if not model_response or "error" in model_response:
                error_msg = model_response.get("error", "Unknown error") if model_response else "Empty response"
                await self.sp_service.update_task_status(
                    task_id=task_id,
                    status="failed",
                    error_message=error_msg,
                    completed_at="now()"
                )
                logger.error(f"Model processing failed for task {task_id}: {error_msg}")
                return {"error": error_msg}
            
            # Get the response ID from the submission
            logger.info(f"Getting latest response ID for case {case_id}")
            response_id = await self._get_latest_response_id(tenant_id, case_id)
            logger.info(f"Latest response ID: {response_id}")
            
            # Update task as completed
            await self.sp_service.update_task_status(
                task_id=task_id,
                status="completed",
                response_id=response_id,
                completed_at="now()"
            )
            
            logger.info(f"Successfully completed task {task_id}")
            return {"success": True, "response": model_response}
            
        except Exception as e:
            logger.error(f"Exception in process_task {task_id}: {e}", exc_info=True)
            
            # Try to update task as failed
            try:
                await self.sp_service.update_task_status(
                    task_id=task_id,
                    status="failed",
                    error_message=str(e),
                    completed_at="now()"
                )
            except Exception as update_error:
                logger.error(f"Failed to update task status: {update_error}")
            
            return {"error": str(e)}
        

    async def get_tasks_status(self, tenant_id: str, task_ids: list[str]) -> dict:
        """Get status of multiple tasks by IDs."""
        try:
            logger.info(f"Getting status for {len(task_ids)} tasks for tenant {tenant_id}")
            
            tasks = []
            for task_id in task_ids:
                task = await self.sp_service.get_by_id(
                    table_name="task",
                    columns="id, case_id, status, error_message, created_at, completed_at",
                    id=task_id
                )
                if task:
                    tasks.append(task)
                else:
                    logger.warning(f"Task not found: {task_id}")
            
            status_summary = {
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0
            }
            
            task_details = {}
            for task in tasks:
                status = task["status"]
                status_summary[status] += 1
                task_details[task["case_id"]] = {
                    "task_id": task["id"],
                    "status": status,
                    "error": task.get("error_message"),
                    "created_at": task["created_at"],
                    "completed_at": task.get("completed_at")
                }
            
            return {
                "summary": status_summary,
                "tasks": task_details,
                "total": len(tasks),
                "found": len(tasks),
                "requested": len(task_ids)
            }
            
        except Exception as e:
            logger.error(f"Error getting tasks status: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _get_latest_response_id(self, tenant_id: str, case_id: str) -> str:
        """Get the latest response ID for a case."""
        try:
            response = await self.sp_service.get_latest_response(tenant_id, case_id)
            return response["id"] if response else None
        except Exception as e:
            logger.error(f"Error getting latest response ID: {e}")
            return None