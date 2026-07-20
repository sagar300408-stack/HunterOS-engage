import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "hunteros_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
)

@celery_app.task(bind=True, max_retries=3)
def process_data_import(self, job_id: str):
    """
    Background task to process a data import job.
    """
    logger.info(f"Processing data import for job {job_id}")
    return {"status": "success", "job_id": job_id}

@celery_app.task
def generate_weekly_roi_report(workspace_id: str):
    """
    Background task triggered by Celery Beat to generate ROI reports.
    """
    logger.info(f"Generating weekly ROI report for workspace {workspace_id}")
    return {"status": "success", "workspace_id": workspace_id}

# Basic Beat Schedule Configuration
celery_app.conf.beat_schedule = {
    "run-weekly-roi-reports": {
        "task": "app.worker.generate_weekly_roi_report",
        "schedule": 604800.0, # Every 7 days in seconds
        "args": ("ALL_WORKSPACES",)
    },
}
