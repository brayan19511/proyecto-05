from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "finance",
    broker=settings.CELERY_BROKER_URL,
    include=["app.workers.sap_tasks"],
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
    # Separar colas por dominio permite escalar SAP sin afectar futuros workers
    # de correos, reportes, exportaciones, etc.
    task_routes={
        "jobs.sap.process_batch": {"queue": "sap"},
    },
    timezone="America/Lima",
    enable_utc=True,
)
