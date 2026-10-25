path = 'app/main.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''    logger.info("hunteros_engage_ready", routes_registered=True)

    yield  # ── Application runs here ──────────────────────────────────────────

    logger.info("hunteros_engage_shutting_down")
    await dispose_engine()
    logger.info("hunteros_engage_stopped")'''

replacement = '''    logger.info("hunteros_engage_ready", routes_registered=True)

    # ── Optional embedded workers for single-process / standalone execution ─────
    embedded_tasks = []
    import os
    if os.environ.get("ENABLE_EMBEDDED_WORKERS", "").lower() == "true":
        logger.info("starting_embedded_background_workers")
        from app.events.dispatcher.poller import OutboxPoller
        from app.integrations.postgres.database import get_session_factory
        from app.celery_app import celery_app
        
        poller = OutboxPoller(
            session_factory=get_session_factory(),
            celery_app=celery_app
        )
        poller_task = asyncio.create_task(poller.run(), name="embedded_outbox_poller")
        followup_task = asyncio.create_task(followup_worker_loop(), name="embedded_followup_worker")
        embedded_tasks.extend([poller_task, followup_task])

    yield  # ── Application runs here ──────────────────────────────────────────

    logger.info("hunteros_engage_shutting_down")
    for t in embedded_tasks:
        t.cancel()
    if embedded_tasks:
        await asyncio.gather(*embedded_tasks, return_exceptions=True)
    await dispose_engine()
    logger.info("hunteros_engage_stopped")'''

assert target in content, "Target block not found in app/main.py"
content = content.replace(target, replacement, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Updated app/main.py successfully.")
