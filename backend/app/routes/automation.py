from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from app.services.scheduler_service import scheduler_manager
from app.database import db_manager

router = APIRouter(prefix="/api/automation", tags=["Automation"])


@router.get("/status")
async def get_automation_status():
    """Return scheduler status, active background jobs, and next run times."""
    return scheduler_manager.get_status()


@router.post("/run/{job_id}")
async def trigger_job_manually(job_id: str):
    """Manually trigger a registered background automation task immediately."""
    result = await scheduler_manager.trigger_job_now(job_id)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Job execution failed"))
    return result


@router.get("/logs")
async def get_automation_logs(
    limit: int = Query(20, ge=1, le=100),
    job_id: Optional[str] = None,
):
    """Retrieve execution logs for background automation tasks."""
    coll = db_manager.automation_logs
    query = {}
    if job_id:
        query["job_id"] = job_id

    docs = await coll.find(query).sort("executed_at", -1).limit(limit).to_list(limit)
    for d in docs:
        d.pop("_id", None)
    return {"data": docs, "total": len(docs)}

