import asyncio
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.service.case_service import CaseService

# Task registry (in-memory)
_TASKS: Dict[str, Dict[str, Any]] = {}

# Bounded concurrency (default 3). Tune as needed.
_GLOBAL_SEMAPHORE: asyncio.Semaphore = asyncio.Semaphore(3)

def set_concurrency(n: int) -> None:
    global _GLOBAL_SEMAPHORE
    _GLOBAL_SEMAPHORE = asyncio.Semaphore(max(1, int(n)))

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_task_status(task_id: str) -> Dict[str, Any]:
    t = _TASKS.get(task_id)
    if not t:
        return {"id": task_id, "state": "NOT_FOUND", "meta": None, "ready": False, "result": None, "error": None}
    return {
        "id": task_id,
        "state": t["state"],
        "meta": t.get("meta"),
        "ready": t["state"] in ("SUCCESS", "FAILURE"),
        "result": t.get("result") if t["state"] == "SUCCESS" else None,
        "error": t.get("error") if t["state"] == "FAILURE" else None,
    }

def get_tasks_status(task_ids: List[str]) -> List[Dict[str, Any]]:
    return [get_task_status(tid) for tid in task_ids]

async def _run_case_history(task_id: str, case_id: str, sem: asyncio.Semaphore) -> None:
    svc = CaseService()
    try:
        async with sem:
            _TASKS[task_id]["state"] = "RUNNING"
            _TASKS[task_id]["started_at"] = _now_iso()
            _TASKS[task_id]["meta"] = {"step": "fetch_files"}

            # Execute the existing history flow (uses Redis PDF cache)
            await svc.proceed_with_model_history_files(case_id)

            _TASKS[task_id]["state"] = "SUCCESS"
            _TASKS[task_id]["ended_at"] = _now_iso()
            _TASKS[task_id]["result"] = {"case_id": case_id, "success": True}
    except Exception as e:
        _TASKS[task_id]["state"] = "FAILURE"
        _TASKS[task_id]["ended_at"] = _now_iso()
        _TASKS[task_id]["error"] = str(e)

def submit_case_history(case_id: str) -> str:
    """
    Enqueue a background task (in-process) to process a case by history files.
    Returns a task_id for frontend polling.
    """
    task_id = str(uuid.uuid4())
    _TASKS[task_id] = {
        "id": task_id,
        "state": "PENDING",
        "meta": {"step": "queued"},
        "enqueued_at": _now_iso(),
    }
    loop = asyncio.get_running_loop()
    loop.create_task(_run_case_history(task_id, case_id, _GLOBAL_SEMAPHORE))
    return task_id
