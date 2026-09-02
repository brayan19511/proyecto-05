"""Limpieza de las carpetas de staging de pagos a proveedores.

Cada envio asincrono crea ``var/payment-provider-jobs/<staging_id>/`` con los
PDFs subidos. Cuando el correo sale bien el PDF se mueve al archivo permanente
(ver ``archive_service``), pero eso deja la carpeta vacia, y los caminos que no
terminan bien dejan los PDFs adentro:

- el envio falla y se agotan los reintentos,
- el job se cancela,
- el lote excede el tiempo limite,
- el proceso muere entre ``_save_uploaded_files`` y ``create_job``, y la
  carpeta queda huerfana, sin ningun job que la referencie.

Nada de eso se puede borrar en el momento: mientras al job le queden reintentos
los PDFs TIENEN que seguir en disco. Por eso la limpieza es un barrido aparte
que decide por el estado del job, no por el resultado de un item.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import shutil

from sqlalchemy.orm import Session

from app.api.jobs.constants import TERMINAL_JOB_STATUSES, JobType
from app.core.config import settings
from app.models.jobs import Job


logger = logging.getLogger(__name__)


class PaymentProviderStagingCleanup:
    """Barre el staging aplicando tres reglas, de la mas informada a la menos."""

    def __init__(self, db: Session):
        self.db = db

    def run(self) -> dict:
        storage_dir = Path(settings.PAYMENT_PROVIDER_STORAGE_DIR)
        if not storage_dir.is_dir():
            return self._summary()

        now = datetime.now(timezone.utc)
        retention_cutoff = now - timedelta(
            days=settings.PAYMENT_PROVIDER_RETENTION_DAYS
        )
        hard_cutoff = now - timedelta(
            days=settings.PAYMENT_PROVIDER_STAGING_MAX_AGE_DAYS
        )

        directories = self._list_staging_dirs(storage_dir)
        if not directories:
            return self._summary()

        jobs_by_staging = self._load_jobs({path.name for path in directories})

        removed_terminal = 0
        removed_orphan = 0
        removed_expired = 0
        kept = 0
        freed_bytes = 0

        for path in directories:
            job = jobs_by_staging.get(path.name)
            reason = self._decide(path, job, retention_cutoff, hard_cutoff)

            if reason is None:
                kept += 1
                continue

            size = self._directory_size(path)
            if not self._remove(path):
                kept += 1
                continue

            freed_bytes += size
            if reason == "terminal":
                removed_terminal += 1
            elif reason == "orphan":
                removed_orphan += 1
            else:
                removed_expired += 1

        summary = self._summary(
            scanned=len(directories),
            removed_terminal=removed_terminal,
            removed_orphan=removed_orphan,
            removed_expired=removed_expired,
            kept=kept,
            freed_bytes=freed_bytes,
        )
        logger.info("Limpieza de staging de pagos a proveedores: %s", summary)

        return summary

    # =====================================================
    # DECISION
    # =====================================================
    def _decide(
        self,
        path: Path,
        job: Job | None,
        retention_cutoff: datetime,
        hard_cutoff: datetime,
    ) -> str | None:
        """Devuelve el motivo del borrado, o None para conservar la carpeta."""
        modified_at = self._modified_at(path)

        # Regla 3 primero, porque es un tope absoluto: cubre los jobs que
        # quedaron en DISPATCH_FAILED y nadie reintento, que con las otras dos
        # reglas se quedarian en disco para siempre.
        if modified_at < hard_cutoff:
            return "expired"

        # Regla 1: hay job y ya termino. Se mide por finished_at, no por la
        # fecha de la carpeta, porque un job largo pudo terminar mucho despues.
        if job is not None:
            if job.status not in TERMINAL_JOB_STATUSES:
                return None

            finished_at = job.finished_at or job.updated_at
            if finished_at is None:
                return None

            if self._as_utc(finished_at) < retention_cutoff:
                return "terminal"

            return None

        # Regla 2: no hay job. Es huerfana, pero puede ser un envio que se esta
        # creando en este instante, asi que igual se respeta la ventana.
        if modified_at < retention_cutoff:
            return "orphan"

        return None

    # =====================================================
    # AUXILIARES
    # =====================================================
    @staticmethod
    def _list_staging_dirs(storage_dir: Path) -> list[Path]:
        """Subcarpetas de staging, excluyendo el archivo permanente.

        La comparacion es por ruta resuelta y no por nombre: el archivo vive
        dentro del staging por defecto, pero se puede reapuntar por .env.
        """
        archive_dir = Path(settings.payment_provider_archive_dir).resolve()

        directories = []
        for path in storage_dir.iterdir():
            if not path.is_dir():
                continue

            resolved = path.resolve()
            if resolved == archive_dir or resolved in archive_dir.parents:
                continue

            directories.append(path)

        return directories

    def _load_jobs(self, staging_ids: set[str]) -> dict[str, Job]:
        """Job de cada staging_id, en una sola consulta."""
        if not staging_ids:
            return {}

        jobs = (
            self.db.query(Job)
            .filter(
                Job.job_type == JobType.PAYMENT_PROVIDER_EMAIL.value,
                Job.parameters["staging_id"].astext.in_(staging_ids),
            )
            .all()
        )

        return {job.parameters["staging_id"]: job for job in jobs}

    @staticmethod
    def _modified_at(path: Path) -> datetime:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        # updated_at se guarda sin zona; se asume UTC, que es como lo escribe
        # el servidor de base de datos.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _directory_size(path: Path) -> int:
        total = 0
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
            except OSError:
                continue
        return total

    @staticmethod
    def _remove(path: Path) -> bool:
        try:
            shutil.rmtree(path)
            return True
        except OSError as error:
            # Un fallo de permisos o un archivo en uso no debe cortar el
            # barrido: se reporta y la carpeta se reintenta en la proxima vuelta.
            logger.warning("No se pudo borrar el staging %s: %s", path, error)
            return False

    @staticmethod
    def _summary(
        *,
        scanned: int = 0,
        removed_terminal: int = 0,
        removed_orphan: int = 0,
        removed_expired: int = 0,
        kept: int = 0,
        freed_bytes: int = 0,
    ) -> dict:
        return {
            "scanned": scanned,
            "removed_terminal": removed_terminal,
            "removed_orphan": removed_orphan,
            "removed_expired": removed_expired,
            "removed_total": removed_terminal + removed_orphan + removed_expired,
            "kept": kept,
            "freed_bytes": freed_bytes,
        }
