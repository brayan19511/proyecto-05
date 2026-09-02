"""Tareas de mantenimiento: liberar disco de lo que ya no se necesita.

Van en la cola light y en beat, no como JobType: no hay nada que reportar por
item ni progreso que seguir, es un barrido que corre solo y deja su resultado
en el log.
"""

from app.api.finance.payment_provider.cleanup_service import (
    PaymentProviderStagingCleanup,
)
from app.core.db.db_postgres import SessionLocal
from app.core.modules import MODULE_PAYMENT_PROVIDER, is_module_enabled
from app.workers.celery_app import celery_app


@celery_app.task(
    name="maintenance.payment_provider.cleanup_staging",
    acks_late=False,
    max_retries=0,
    soft_time_limit=600,
    time_limit=660,
)
def cleanup_payment_provider_staging():
    """Borra las carpetas de staging que ya cumplieron su retencion."""
    with SessionLocal() as db:
        # Con el modulo apagado no se envian correos, asi que tampoco hay que
        # tocar sus archivos: se deja todo como esta hasta que lo prendan.
        if not is_module_enabled(MODULE_PAYMENT_PROVIDER, db):
            return {"status": "skipped", "reason": "modulo desactivado"}

        return PaymentProviderStagingCleanup(db).run()
