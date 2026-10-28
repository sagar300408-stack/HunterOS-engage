import asyncio
import logging
import warnings
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
    imports=[
        "app.domain.intent.tasks"
    ],
    task_queues=(
        Queue('celery', routing_key='celery'),  # default queue
        Queue('event_dispatch', routing_key='event_dispatch'), # high-throughput event dispatch queue
    )
)

from celery.signals import worker_process_init, worker_process_shutdown

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


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    """
    Cleanup async database engine connection pool on worker process shutdown.
    """
    from app.integrations.postgres.database import reset_engine
    reset_engine()


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
    },
    "process-due-followups": {
        "task": "app.celery_app.process_due_followups_task",
        "schedule": 30.0, # Every 30 seconds
    }
}

@celery_app.task
def generate_weekly_roi_report(workspace_id: str):
    """
    Background task triggered by Celery Beat to generate ROI reports.
    """
    logger.info(f"Generating weekly ROI report for workspace {workspace_id}")
    return {"status": "success", "workspace_id": workspace_id}


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """
    Get or create a persistent event loop for the current Celery worker process.

    Reusing a long-lived event loop ensures that pooled asyncpg connections
    associated with the shared SQLAlchemy AsyncEngine remain bound to a single,
    open event loop across sequential task executions.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                from app.integrations.postgres.database import reset_engine
                reset_engine()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    return loop


@celery_app.task(name="app.celery_app.process_due_followups_task")
def process_due_followups_task():
    """
    Periodic task triggered by Celery Beat to execute due follow-up messages.
    """
    try:
        from app.worker.followup_worker import process_due_followups
        loop = get_worker_event_loop()
        return loop.run_until_complete(process_due_followups())
    except Exception as exc:
        logger.error(f"process_due_followups_task_error: {exc}", exc_info=True)
        raise
