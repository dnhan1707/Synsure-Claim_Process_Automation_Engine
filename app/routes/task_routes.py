from fastapi import APIRouter, Query, Path, HTTPException
from fastapi.responses import JSONResponse
from app.service.task_service_v2 import TaskService
from app.models.request_models import ProcessTaskRequest
import logging

logger = logging.getLogger(__name__)

def create_task_router() -> APIRouter:
    router = APIRouter(
        prefix="/task",
        tags=["Tasks"]
    )

    @router.get("/status/{tenant_id}")
    async def get_tasks_status(
        tenant_id: str = Path(..., description="Tenant ID"),
        task_ids: str = Query(..., description="Comma-separated task IDs", min_length=1)
    ):
        """Get status of multiple tasks."""
        try:
            # Parse and validate task IDs
            task_id_list = [tid.strip() for tid in task_ids.split(",") if tid.strip()]
            
            if not task_id_list:
                raise HTTPException(
                    status_code=400, 
                    detail="No valid task IDs provided"
                )
            
            if len(task_id_list) > 50:  # Prevent abuse
                raise HTTPException(
                    status_code=400, 
                    detail="Too many task IDs (maximum 50 allowed)"
                )
            
            task_service = TaskService()
            result = await task_service.get_tasks_status(tenant_id, task_id_list)
            
            if isinstance(result, dict) and "error" in result:
                return JSONResponse(result, status_code=500)
                
            return JSONResponse(result, status_code=200)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_tasks_status: {e}", exc_info=True)
            return JSONResponse(
                {"error": f"Internal server error: {str(e)}"}, 
                status_code=500
            )
    
    # @router.post("/debug/process-task", tags=["Debug"])
    # async def debug_process_task(request: ProcessTaskRequest):
    #     """Debug endpoint to manually process a single task."""
    #     try:
    #         task_service = TaskService()
    #         result = await task_service.process_task(request.task_id)
            
    #         return JSONResponse(
    #             {"task_id": request.task_id, "result": result}, 
    #             status_code=200
    #         )
            
    #     except Exception as e:
    #         logger.error(f"Error in debug_process_task: {e}", exc_info=True)
    #         return JSONResponse(
    #             {"error": str(e), "task_id": request.task_id}, 
    #             status_code=500
    #         )

    # @router.get("/debug/task/{task_id}", tags=["Debug"])
    # async def debug_get_task(
    #     task_id: str = Path(..., description="Task ID to retrieve")
    # ):
    #     """Debug endpoint to get task details."""
    #     try:
    #         task_service = TaskService()
    #         task = await task_service.sp_service.get_by_id("task", "*", task_id)
            
    #         if not task:
    #             raise HTTPException(
    #                 status_code=404, 
    #                 detail=f"Task not found: {task_id}"
    #             )
            
    #         return JSONResponse({"task": task}, status_code=200)
            
    #     except HTTPException:
    #         raise
    #     except Exception as e:
    #         logger.error(f"Error in debug_get_task: {e}", exc_info=True)
    #         return JSONResponse(
    #             {"error": str(e)}, 
    #             status_code=500
    #         )
    
    return router