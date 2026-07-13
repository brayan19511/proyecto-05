import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.finance.payment_provider.payment_provider_schema import PaymentProviderRequest
from app.api.finance.payment_provider.payment_provider_service import PaymentProviderService


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payment_provider",
    tags=["PAYMENT PROVIDER"],
)


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the payment provider service.
    Returns a simple message indicating that the service is running.
    """
    logger.info("Health check endpoint called.")
    return {"status": "Payment provider service is healthy."}
# async def process_payment(request: PaymentProviderRequest):
@router.post("/process_payment")
async def process_payment(
    files: list[UploadFile] = File(...),
):
    """
    Procesa múltiples constancias de pago,
    extrae sus datos y las agrupa por proveedor.
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail=(
                "Debe adjuntar al menos un archivo."
            ),
        )

    service = PaymentProviderService(
        files=files
    )

    resultado = service.process()

    return {
        "status": "Payment files processed.",
        **resultado,
    }