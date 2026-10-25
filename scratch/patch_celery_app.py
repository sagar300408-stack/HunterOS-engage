path = 'app/celery_app.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''    "recover-stale-events": {
        "task": "app.events.worker.maintenance.recover_stale_events",
        "schedule": 300.0, # Every 5 minutes
    }
}'''

replacement = '''    "recover-stale-events": {
        "task": "app.events.worker.maintenance.recover_stale_events",
        "schedule": 300.0, # Every 5 minutes
    },
    "process-due-followups": {
        "task": "app.celery_app.process_due_followups_task",
        "schedule": 30.0, # Every 30 seconds
    }
}'''

assert target in content
content = content.replace(target, replacement, 1)

target2 = '''@celery_app.task
def generate_weekly_roi_report(workspace_id: str):
    """
    Background task triggered by Celery Beat to generate ROI reports.
    """
    logger.info(f"Generating weekly ROI report for workspace {workspace_id}")
    return {"status": "success", "workspace_id": workspace_id}'''

replacement2 = '''@celery_app.task
def generate_weekly_roi_report(workspace_id: str):
    """
    Background task triggered by Celery Beat to generate ROI reports.
    """
    logger.info(f"Generating weekly ROI report for workspace {workspace_id}")
    return {"status": "success", "workspace_id": workspace_id}


@celery_app.task
def process_due_followups_task():
    """
    Periodic task triggered by Celery Beat to execute due follow-up messages.
    """
    import asyncio
    from app.worker.followup_worker import process_due_followups
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(process_due_followups())
    finally:
        loop.close()'''

assert target2 in content
content = content.replace(target2, replacement2, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Updated app/celery_app.py successfully.")
