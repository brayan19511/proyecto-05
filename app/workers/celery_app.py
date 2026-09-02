from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


celery_app = Celery(
    "finance",
    broker=settings.CELERY_BROKER_URL,
    include=[
        "app.workers.sap_tasks",
        "app.workers.analytics_tasks",
        "app.workers.silver_tasks",
        "app.workers.email_tasks",
        "app.workers.ledger_tasks",
        "app.workers.scheduled_tasks",
        "app.workers.maintenance_tasks",
    ],
)

# RabbitMQ solo transporta mensajes pequenos para avisar "procesa este lote".
# El estado real del negocio queda en PostgreSQL, por eso no usamos result
# backend de Celery ni guardamos resultados sensibles en RabbitMQ.
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_ignore_result=True,
    task_track_started=False,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    worker_max_memory_per_child=settings.CELERY_WORKER_MAX_MEMORY_PER_CHILD_KB,
    # Las colas se separan por perfil operativo, no por modulo.
    # light recibe trabajos cortos, email queda aislada y heavy agrupa procesos largos.
    task_default_queue="light",
    task_routes={
        "jobs.sap.process_batch": {"queue": "heavy"},
        "jobs.analytics.process_batch": {"queue": "heavy"},
        "jobs.analytics_silver.process_batch": {"queue": "heavy"},
        "jobs.payment_provider.send_email_batch": {"queue": "email"},
        "jobs.ledger.process_batch": {"queue": "heavy"},
        "scheduled_jobs.tick": {"queue": "light"},
        "maintenance.payment_provider.cleanup_staging": {"queue": "light"},
    },
    beat_schedule={
        "scheduled-jobs-tick": {
            "task": "scheduled_jobs.tick",
            "schedule": settings.CELERY_SCHEDULER_INTERVAL_SECONDS,
        },
        # Una vez al dia y de madrugada: es un barrido de disco, no hay
        # apuro y asi no compite con los envios en horario de oficina.
        "payment-provider-cleanup-staging": {
            "task": "maintenance.payment_provider.cleanup_staging",
            "schedule": crontab(hour=3, minute=30),
        },
    },
    timezone="America/Lima",
    enable_utc=True,
)
