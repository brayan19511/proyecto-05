"""Archivo permanente de las constancias de pago que ya se enviaron.

El PDF nace en el staging (``var/payment-provider-jobs/<staging_id>/``), que es
un directorio de paso que la limpieza borra a los pocos dias. Cuando el correo
sale bien el archivo se MUEVE de ahi al archivo permanente y queda registrado
en ``storage.attachments`` colgado del JobItem, o sea del correo concreto que
se envio: por ese id ya se conoce proveedor, destinatarios y fecha.

Se mueve y no se copia porque el archivo permanente vive en el mismo volumen
que el staging: ``Path.replace`` es un rename atomico dentro del mismo
filesystem, asi que no existe el estado intermedio "copiado a medias".
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.api.finance.payment_provider.constants import (
    PAYMENT_PROVIDER_EMAIL_ENTITY_TYPE,
)
from app.api.storage.attachments_repository import AttachmentRepository
from app.core.config import settings
from app.models.storage import Attachment


class PaymentProviderArchiveService:
    """Mueve las constancias enviadas al archivo permanente y las lista."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = AttachmentRepository(db)

    # =====================================================
    # ESCRITURA
    # =====================================================
    def archive_item_attachments(
        self,
        item_id: UUID,
        attachments: list[dict],
        *,
        user_id: UUID | None = None,
    ) -> list[Attachment]:
        """Archiva los adjuntos de un correo enviado. Devuelve las filas creadas.

        No hace commit: lo hace el llamador junto con el resto del avance del
        item, para que el registro del adjunto y el "correo enviado" queden en
        la misma transaccion.
        """
        archived = []

        for attachment in attachments:
            source = Path(attachment["file_path"])
            if not source.exists():
                # Un reintento puede encontrarlo ya archivado; no es un error.
                continue

            file_name = attachment.get("filename") or source.name
            size = source.stat().st_size
            target = self._move_to_archive(source)

            row = Attachment(
                entity_type=PAYMENT_PROVIDER_EMAIL_ENTITY_TYPE,
                entity_id=item_id,
                file_name=file_name,
                file_extension=(target.suffix.lstrip(".") or "pdf"),
                mime_type=attachment.get("content_type") or "application/pdf",
                storage_type="disk",
                file_size=size,
                file_path=str(target),
                created_by=user_id,
            )
            self.repository.create(row)
            archived.append(row)

        return archived

    @staticmethod
    def _move_to_archive(source: Path) -> Path:
        """Mueve el PDF a <archivo>/<anio>/<mes>/<uuid><ext>.

        Se reparte por anio/mes para que ningun directorio termine con decenas
        de miles de archivos, que vuelve lento cualquier listado.
        """
        now = datetime.now(timezone.utc)
        target_dir = (
            Path(settings.payment_provider_archive_dir)
            / f"{now.year:04d}"
            / f"{now.month:02d}"
        )
        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / f"{uuid4()}{source.suffix.lower() or '.pdf'}"
        source.replace(target)

        return target

    # =====================================================
    # LECTURA
    # =====================================================
    def list_item_attachments(self, item_id: UUID) -> list[Attachment]:
        return self.repository.get_by_entity(
            PAYMENT_PROVIDER_EMAIL_ENTITY_TYPE,
            item_id,
        )

    def get_attachment(self, attachment_id: UUID) -> Attachment | None:
        attachment = self.repository.get_by_id(attachment_id)

        # Se acota al tipo propio: este servicio no da acceso a los adjuntos
        # de provisiones, que tienen su propio control de alcance.
        if (
            attachment is None
            or attachment.entity_type != PAYMENT_PROVIDER_EMAIL_ENTITY_TYPE
        ):
            return None

        return attachment

    @staticmethod
    def read_bytes(attachment: Attachment) -> bytes | None:
        if not attachment.file_path:
            return None

        path = Path(attachment.file_path)
        if not path.is_file():
            return None

        return path.read_bytes()
