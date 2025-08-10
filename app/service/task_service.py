from typing import Any, Dict, List
from celery.result import AsyncResult
from app.celery_app import celery_app


def get_task_status(task_id: str) -> Dict[str, Any]:
    res = AsyncResult(task_id, app=celery_app)
    info = res.info if isinstance(res.info, dict) else None
    # states: PENDING, STARTED, RETRY, FAILURE, SUCCESS, PROGRESS (custom)
    return {
        "id": task_id,
        "state": res.state,
        "meta": info,
        "ready": res.ready(),
            # result available only when ready; can be a dict or exception str
        "result": res.result if res.ready() and not res.failed() else None,
        "error": str(res.result) if res.failed() else None,
    }


def get_tasks_status(task_ids: List[str]) -> List[Dict[str, Any]]:
    return [get_task_status(tid) for tid in task_ids]