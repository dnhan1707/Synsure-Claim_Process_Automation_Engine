from app.celery_app import celery_app
from app.service.case_service import CaseService
import asyncio
from typing import Dict, Any


@celery_app.task(bind=True, name="case.process_history")
def process_case_history(self, case_id: str):
    """
    Celery task: process one case by reusing history files.
    Returns a small dict; progress reported via task state/meta.
    """
    async def _run() -> Dict[str, Any]:
        svc = CaseService()
        try:
            self.update_state(state="STARTED", meta={"step": "fetch_files"})
            result = await svc.proceed_with_model_history_files(case_id)
        
            return {"case_id": case_id, "success": True}
        
        except Exception as e:
            return {"case_id": case_id, "success": False, "error": str(e)}

    self.update_state(state="PROGRESS", meta={"step": "running"})
    out = asyncio.run(_run())
    
    # final state is "SUCCESS" automatically when returning
    return out