import logging
from celery import Celery
from kombu import Queue

from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

celery_app = Celery(
    "hunteros_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
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
        "app.events.worker.tasks.dispatch_event": {"queue": "event_dispatch"},
    },
    task_queues=(
        Queue('celery', routing_key='celery'),  # default queue
        Queue('event_dispatch', routing_key='event_dispatch'), # high-throughput event dispatch queue
    )
)

from celery.signals import worker_process_init

@worker_process_init.connect
def init_worker(**kwargs):
    """
    Bootstrap the consumer registry for the celery worker processes.
    """
    from app.events.registry.registry import registry
    from app.events.bootstrap.register_consumers import bootstrap_event_consumers
    
    logger.info("Initializing Declarative ConsumerRegistry in Celery Worker")
    bootstrap_event_consumers(registry)
    
    # Register followup subscribers manually
    from app.events.followup_subscribers import register_subscribers
    for consumer in register_subscribers():
        for event_class in consumer.get_subscriptions():
            registry.register(event_class, consumer)

    logger.info("Declarative ConsumerRegistry successfully initialized.")


# Register all Celery tasks
celery_app.autodiscover_tasks([
    'app.events.worker.tasks',
    'app.events.worker.maintenance',
])


# Basic Beat Schedule Configuration
celery_app.conf.beat_schedule = {
    "run-weekly-roi-reports": {
        "task": "app.celery_app.generate_weekly_roi_report",
        "schedule": 604800.0, # Every 7 days in seconds
        "args": ("ALL_WORKSPACES",)
    },
    "recover-stale-events": {
        "task": "app.events.worker.maintenance.recover_stale_events",
        "schedule": 300.0, # Every 5 minutes
    }
}

@celery_app.task
def generate_weekly_roi_report(workspace_id: str):
    """
    Background task triggered by Celery Beat to generate ROI reports.
    """
    logger.info(f"Generating weekly ROI report for workspace {workspace_id}")
    return {"status": "success", "workspace_id": workspace_id}
