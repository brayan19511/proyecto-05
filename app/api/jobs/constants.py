from enum import StrEnum

from app.core.modules import (
    MODULE_ANALYTICS,
    MODULE_LEDGER,
    MODULE_PAYMENT_PROVIDER,
    MODULE_SAP,
)


class JobType(StrEnum):
    SAP_DOCUMENT_ACTION = "SAP_DOCUMENT_ACTION"
    SAP_RECONCILIATION = "SAP_RECONCILIATION"
    PAYMENT_PROVIDER_EMAIL = "PAYMENT_PROVIDER_EMAIL"
    LEDGER_SYNC = "LEDGER_SYNC"
    LEDGER_SYNC_DELTA = "LEDGER_SYNC_DELTA"
    LEDGER_REPROCESS = "LEDGER_REPROCESS"
    ANALYTICS_EXTRACT = "ANALYTICS_EXTRACT"
    ANALYTICS_SILVER_BUILD = "ANALYTICS_SILVER_BUILD"


class JobTriggerSource(StrEnum):
    API = "API"
    SCHEDULED = "SCHEDULED"
    SCHEDULED_MANUAL = "SCHEDULED_MANUAL"
    RETRY = "RETRY"


class ScheduledJobScheduleKind(StrEnum):
    DAILY = "DAILY"
    INTERVAL_MINUTES = "INTERVAL_MINUTES"
    WINDOW_INTERVAL = "WINDOW_INTERVAL"


class JobStatus(StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    DISPATCH_FAILED = "DISPATCH_FAILED"
    RUNNING = "RUNNING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class JobBatchStatus(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobItemStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_JOB_STATUSES = {
    JobStatus.CANCELLED,
    JobStatus.COMPLETED,
    JobStatus.COMPLETED_WITH_ERRORS,
    JobStatus.FAILED,
}

TERMINAL_BATCH_STATUSES = {
    JobBatchStatus.COMPLETED,
    JobBatchStatus.COMPLETED_WITH_ERRORS,
    JobBatchStatus.FAILED,
    JobBatchStatus.CANCELLED,
}

JOBS_VIEW_PERMISSION = "jobs.view"
JOBS_VIEW_ALL_PERMISSION = "jobs.view_all"
JOBS_CANCEL_PERMISSION = "jobs.cancel"
JOBS_CANCEL_ALL_PERMISSION = "jobs.cancel_all"
JOBS_RETRY_PERMISSION = "jobs.retry"
SCHEDULED_JOBS_VIEW_PERMISSION = "scheduled_jobs.view"
SCHEDULED_JOBS_EDIT_PERMISSION = "scheduled_jobs.edit"
SCHEDULED_JOBS_RUN_PERMISSION = "scheduled_jobs.run"
ANALYTICS_INGEST_VIEW_PERMISSION = "analytics.ingest.view"
ANALYTICS_INGEST_RUN_PERMISSION = "analytics.ingest.run"


# =====================================================
# MODULO AL QUE PERTENECE CADA TIPO DE TAREA
# =====================================================
# Vive aqui y no en el dispatcher porque lo consultan tanto el dispatcher
# como el scheduler, y este modulo no importa nada del resto de la app.
JOB_MODULES = {
    JobType.SAP_DOCUMENT_ACTION.value: MODULE_SAP,
    JobType.SAP_RECONCILIATION.value: MODULE_SAP,
    JobType.PAYMENT_PROVIDER_EMAIL.value: MODULE_PAYMENT_PROVIDER,
    JobType.LEDGER_SYNC.value: MODULE_LEDGER,
    JobType.LEDGER_SYNC_DELTA.value: MODULE_LEDGER,
    JobType.LEDGER_REPROCESS.value: MODULE_LEDGER,
    JobType.ANALYTICS_EXTRACT.value: MODULE_ANALYTICS,
    JobType.ANALYTICS_SILVER_BUILD.value: MODULE_ANALYTICS,
}

# last_status de una tarea programada que no corrio por modulo apagado.
# No es un fallo: no incrementa consecutive_failures.
SKIPPED_STATUS = "SKIPPED"
