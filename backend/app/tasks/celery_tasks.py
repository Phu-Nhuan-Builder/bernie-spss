"""
Celery Tasks — Long-running statistical computations
Threshold: n_vars × n_cases > 50,000 cells → Celery

DISK SAFETY: task_ignore_result=True, result_backend=None
"""
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    from app.core.config import settings

    celery_app = Celery(
        "statworks",
        broker=settings.REDIS_URL,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_soft_time_limit=120,
        task_time_limit=180,
        worker_max_memory_per_child=400_000,
        # DISK SAFETY — do not persist results
        task_ignore_result=True,
        result_backend=None,
    )

    @celery_app.task(bind=True, ignore_result=True, name="statworks.run_factor_analysis")
    def run_factor_analysis_task(
        self,
        session_id: str,
        variables: list,
        n_factors: int,
        extraction: str,
        rotation: str,
    ) -> dict:
        """
        Long-running EFA task via Celery.
        Called when n_vars × n_cases > 50,000 cells.
        """
        from app.domain.services.spss_io import SESSION_STORE
        from app.domain.services.factor_analysis import run_efa

        if session_id not in SESSION_STORE:
            raise ValueError(f"Session {session_id} not found")

        df, meta = SESSION_STORE[session_id]
        result = run_efa(df, variables, n_factors, extraction, rotation)
        return result

except ImportError as e:
    logger.warning(f"Celery not available: {e}. Async jobs will not work.")
    celery_app = None

    def run_factor_analysis_task(*args, **kwargs):
        raise RuntimeError("Celery not available")
