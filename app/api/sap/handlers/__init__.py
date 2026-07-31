from app.api.jobs.constants import JobType
from app.api.sap.handlers.base import SapItemHandler
from app.api.sap.handlers.document_action import SapDocumentActionHandler
from app.api.sap.handlers.reconciliation import SapReconciliationHandler
from app.core.exceptions import ValidationError


SAP_ITEM_HANDLERS: dict[str, type[SapItemHandler]] = {
    JobType.SAP_DOCUMENT_ACTION.value: SapDocumentActionHandler,
    JobType.SAP_RECONCILIATION.value: SapReconciliationHandler,
}


def get_sap_item_handler(job_type: str) -> type[SapItemHandler]:
    """Devuelve el handler que sabe ejecutar un tipo de job SAP."""
    handler = SAP_ITEM_HANDLERS.get(job_type)
    if not handler:
        raise ValidationError(f"Tipo de tarea SAP no soportado: {job_type}")
    return handler
