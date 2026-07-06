from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "finance",
    broker=settings.CELERY_BROKER_URL,
    include=["app.workers.sap_tasks"],
)

# RabbitMQ only transports task identifiers. Business status and results live
# in PostgreSQL, so Celery's result backend is intentionally disabled.
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_ignore_result=True,
    task_track_started=False,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    # Domain queues let SAP scale independently from future exports or emails.
    task_routes={
        "jobs.sap.process_batch": {"queue": "sap"},
    },
    timezone="America/Lima",
    enable_utc=True,
)
