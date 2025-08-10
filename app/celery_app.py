from celery import Celery
from app.config.settings import get_settings

def _redis_url(db: int) -> str:
    cfg = get_settings().redis
    host = cfg.host or "localhost"
    port = cfg.port or "6379"
    pwd = cfg.password or ""
    auth = f":{pwd}@" if pwd else ""
    return f"redis://{auth}{host}:{port}/{db}"

BROKER_URL = _redis_url(0)          # cloud Redis usually exposes only DB 0
RESULT_BACKEND = _redis_url(0)      # use the same DB 0

celery_app = Celery(
    "demo_startup",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks.case_tasks"],  # ensure tasks are registered
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    worker_send_task_events=True,
    result_expires=60 * 60 * 24,
    timezone="UTC",
    enable_utc=True,
    broker_pool_limit=2,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"max_connections": 5, "visibility_timeout": 3600},
    result_backend_transport_options={"max_connections": 5},
    worker_prefetch_multiplier=1,
)