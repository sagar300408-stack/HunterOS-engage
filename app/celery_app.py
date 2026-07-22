import logging
from celery import Celery
from kombu import Queue

from app.core.config import settings

# Import the new dispatch task
from app.events.tasks import dispatch_event

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
    task_routes={
        "app.events.tasks.dispatch_event": {"queue": "event_dispatch"},
    },
    task_queues=(
        Queue('celery', routing_key='celery'),  # default queue
        Queue('event_dispatch', routing_key='event_dispatch'), # high-throughput event dispatch queue
    )
)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Setup periodic tasks if any
    pass

from celery.signals import worker_process_init

@worker_process_init.connect
def init_worker(**kwargs):
    """
    Bootstrap the consumer registry for the celery worker processes.
    """
    from app.events.bus.registry import ConsumerRegistry
    from app.events.bootstrap.register_consumers import bootstrap_event_consumers
    from app.events.tasks import set_celery_registry

    logger.info("Initializing ConsumerRegistry in Celery Worker")
    registry = ConsumerRegistry()
    bootstrap_event_consumers(registry)
    
    # Register followup subscribers manually
    from app.events.followup_subscribers import register_subscribers
    for consumer in register_subscribers():
        registry.register(consumer)

    set_celery_registry(registry)
    logger.info("ConsumerRegistry successfully initialized.")


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
        "task": "app.celery_app.generate_weekly_roi_report",
        "schedule": 604800.0, # Every 7 days in seconds
        "args": ("ALL_WORKSPACES",)
    },
    "poll-due-followups": {
        "task": "app.celery_app.poll_due_followups",
        "schedule": 15.0, # Every 15 seconds
    },
}

@celery_app.task
def poll_due_followups():
    """
    Background task triggered by Celery Beat to process follow-ups.
    """
    import asyncio
    from app.worker.followup_worker import process_due_followups
    
    # We loop here synchronously for a bit to drain the queue 
    # instead of just doing one per 15s.
    count = 0
    while True:
        processed = asyncio.run(process_due_followups())
        if not processed:
            break
        count += 1
        if count >= 50:  # Prevent infinite lockup of the worker
            break
            
    return {"status": "success", "processed_count": count}
