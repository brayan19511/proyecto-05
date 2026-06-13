from fastapi import APIRouter, Depends

from app.api.sap.sap_schema import SapServiceDocumentos
from app.api.sap.service.sap_batch_service import SapBatchService

from app.core.security import get_current_user
from app.models.sap.sap_models import SAPCredentials

router = APIRouter(prefix="/sap", tags=["SAP"])


@router.post("/services")
def service_sap(request: SapServiceDocumentos, current_user=Depends(get_current_user)):

    credentials = SAPCredentials(
        company=request.database,
        user_name=request.user,
        password=request.password,
    )

    service = SapBatchService(credentials=credentials, max_workers=4, batch_size=25)

    return service.execute(request)
