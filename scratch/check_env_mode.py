import sys, os
sys.path.insert(0, os.getcwd())

from app.config import get_settings
settings = get_settings()

print(f"APP_ENV: {settings.app_env}")
print(f"IS_DEVELOPMENT: {settings.is_development}")
print(f"IS_PRODUCTION: {settings.is_production}")
print(f"ENABLE_EMBEDDED_WORKERS env var: '{os.environ.get('ENABLE_EMBEDDED_WORKERS', '')}'")
print(f"DISPATCHER_WORKER_ID: {settings.dispatcher_worker_id}")
print(f"DISPATCHER_POLL_INTERVAL: {settings.dispatcher_poll_interval}")
print(f"CELERY_BROKER_URL present: {bool(settings.celery_broker_url)}")
