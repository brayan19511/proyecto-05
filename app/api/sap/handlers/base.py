from abc import ABC, abstractmethod

from app.api.sap.service.sap_document_service import SapDocumentService
from app.models.jobs import JobBatch, JobItem


class SapItemHandler(ABC):
    """Contrato simple para ejecutar un item SAP dentro de un batch."""

    def __init__(self, service: SapDocumentService, client):
        self.service = service
        self.client = client

    @abstractmethod
    def execute(self, batch: JobBatch, item: JobItem):
        """Ejecuta el item y deja que el procesador maneje estados/errores."""
