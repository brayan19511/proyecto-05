from app.api.sap.constants import SAP_RESOURCE_PATTERN
from app.api.sap.service.sap_service_client import SAPServiceLayerClient
from app.core.exceptions import ValidationError
from app.models.sap.sap_models import SAPCredentials


class SapDocumentService:
    """Ejecuta acciones SAP usando una sesion ya autenticada."""

    def __init__(self, credentials: SAPCredentials):
        self.credentials = credentials

    def build_client(self) -> SAPServiceLayerClient:
        return SAPServiceLayerClient(
            company=self.credentials.company,
            user_name=self.credentials.user_name,
            password=self.credentials.password,
        )

    @staticmethod
    def validate_resource_name(value: str, field_name: str) -> str:
        if not SAP_RESOURCE_PATTERN.fullmatch(value):
            raise ValidationError(f"{field_name} contiene un valor no permitido")
        return value

    def execute(
        self,
        client: SAPServiceLayerClient,
        *,
        entity: str,
        action: str,
        document: str,
    ):
        safe_entity = self.validate_resource_name(entity, "entidad")
        safe_action = self.validate_resource_name(action, "action")
        if not document.isdigit():
            raise ValidationError("El documento debe ser numerico")

        endpoint = f"{safe_entity}({document})/{safe_action}"
        return client.post(endpoint)

    def execute_reconciliation(
        self,
        client: SAPServiceLayerClient,
        *,
        payload: dict,
    ):
        # La reconciliacion interna siempre apunta a este recurso estandar de
        # SAP Service Layer; el Excel solo define las lineas del payload.
        return client.post("InternalReconciliations", data=payload)
