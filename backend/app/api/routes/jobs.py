"""
Async Jobs Routes — Poll Celery task status
"""
import logging
from fastapi import APIRouter

from app.domain.models.job import JobStatus, JobResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{job_id}", response_model=JobResult)
async def get_job_status(job_id: str):
    """Poll Celery AsyncResult for long-running statistical tasks."""
    try:
        from app.tasks.celery_tasks import celery_app
        from celery.result import AsyncResult

        task = AsyncResult(job_id, app=celery_app)
        result = None
        error = None
        progress_msg = None

        state_str = task.state  # "PENDING", "PROGRESS", "SUCCESS", "FAILURE"

        if task.state == "SUCCESS":
            result = task.result
        elif task.state == "FAILURE":
            error = str(task.result) if task.result else "Task failed"
        elif task.state == "PROGRESS":
            progress_msg = task.info.get("step", "") if isinstance(task.info, dict) else None

        # Map Celery states to our JobStatus enum
        status_map = {
            "PENDING": JobStatus.PENDING,
            "STARTED": JobStatus.PROGRESS,
            "PROGRESS": JobStatus.PROGRESS,
            "SUCCESS": JobStatus.SUCCESS,
            "FAILURE": JobStatus.FAILURE,
            "RETRY": JobStatus.PENDING,
            "REVOKED": JobStatus.FAILURE,
        }
        status = status_map.get(state_str, JobStatus.PENDING)

        return JobResult(
            job_id=job_id,
            status=status,
            progress_msg=progress_msg,
            result=result,
            error=error,
        )

    except Exception as e:
        logger.error(f"Job status error for {job_id}: {e}")
        return JobResult(
            job_id=job_id,
            status=JobStatus.FAILURE,
            error=f"Could not retrieve job status: {str(e)}",
        )
