import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from app.api.finance.payment_provider.archive_service import (
    PaymentProviderArchiveService,
)
from app.api.finance.payment_provider.cleanup_service import (
    PaymentProviderStagingCleanup,
)
from app.api.finance.payment_provider.constants import (
    PAYMENT_PROVIDER_EMAIL_ENTITY_TYPE,
)
from app.api.jobs.constants import JobStatus
from app.core.config import settings


class FakeJob:
    def __init__(self, status, finished_at=None, updated_at=None):
        self.status = status
        self.finished_at = finished_at
        self.updated_at = updated_at


class FakeQuery:
    def filter(self, *_args):
        return self

    def all(self):
        return []


class FakeSession:
    """Sesion minima: acumula lo agregado y no devuelve ningun job."""

    def __init__(self):
        self.added = []

    def add(self, entity):
        self.added.append(entity)

    def query(self, _model):
        return FakeQuery()


def _aged(path: Path, days: float) -> Path:
    """Envejece la fecha de modificacion de una carpeta o archivo."""
    timestamp = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    import os

    os.utime(path, (timestamp, timestamp))
    return path


class StagingCleanupDecisionTests(unittest.TestCase):
    """La decision por carpeta, que es donde vive el riesgo de borrar de mas."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cleanup = PaymentProviderStagingCleanup(FakeSession())
        now = datetime.now(timezone.utc)
        self.retention_cutoff = now - timedelta(days=7)
        self.hard_cutoff = now - timedelta(days=30)

    def tearDown(self):
        self.tmp.cleanup()

    def _dir(self, days_old: float) -> Path:
        path = self.root / str(uuid4())
        path.mkdir()
        return _aged(path, days_old)

    def _decide(self, path, job):
        return self.cleanup._decide(
            path,
            job,
            self.retention_cutoff,
            self.hard_cutoff,
        )

    # ---------- regla 1: job terminal ----------
    def test_terminal_job_past_retention_is_removed(self):
        job = FakeJob(
            JobStatus.COMPLETED.value,
            finished_at=datetime.now(timezone.utc) - timedelta(days=8),
        )

        self.assertEqual(self._decide(self._dir(8), job), "terminal")

    def test_terminal_job_inside_retention_is_kept(self):
        job = FakeJob(
            JobStatus.COMPLETED.value,
            finished_at=datetime.now(timezone.utc) - timedelta(days=2),
        )

        self.assertIsNone(self._decide(self._dir(2), job))

    def test_failed_job_is_terminal_too(self):
        # Un job fallido ya agoto sus reintentos: su staging es basura.
        job = FakeJob(
            JobStatus.FAILED.value,
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
        )

        self.assertEqual(self._decide(self._dir(10), job), "terminal")

    def test_running_job_is_never_removed(self):
        # Lo mas importante de todo: borrar aca matarian un reintento en curso.
        job = FakeJob(
            JobStatus.RUNNING.value,
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
        )

        self.assertIsNone(self._decide(self._dir(10), job))

    def test_terminal_job_without_finished_at_uses_updated_at(self):
        job = FakeJob(
            JobStatus.COMPLETED.value,
            finished_at=None,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(days=9),
        )

        self.assertEqual(self._decide(self._dir(9), job), "terminal")

    def test_terminal_job_without_any_date_is_kept(self):
        job = FakeJob(JobStatus.COMPLETED.value, finished_at=None, updated_at=None)

        self.assertIsNone(self._decide(self._dir(9), job))

    # ---------- regla 2: huerfanas ----------
    def test_orphan_past_retention_is_removed(self):
        self.assertEqual(self._decide(self._dir(8), None), "orphan")

    def test_recent_orphan_is_kept(self):
        # Puede ser un envio que se esta creando justo ahora.
        self.assertIsNone(self._decide(self._dir(0), None))

    # ---------- regla 3: tope absoluto ----------
    def test_dispatch_failed_job_is_removed_after_hard_cap(self):
        # DISPATCH_FAILED no es terminal, asi que sin el tope duro esta carpeta
        # se quedaria en disco para siempre.
        job = FakeJob(JobStatus.DISPATCH_FAILED.value)

        self.assertIsNone(self._decide(self._dir(10), job))
        self.assertEqual(self._decide(self._dir(31), job), "expired")

    def test_running_job_is_removed_after_hard_cap(self):
        job = FakeJob(JobStatus.RUNNING.value)

        self.assertEqual(self._decide(self._dir(40), job), "expired")


class StagingCleanupSweepTests(unittest.TestCase):
    """El barrido completo: que borre lo que toca y no toque el archivo."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _staging(self, days_old: float, *, with_file=True) -> Path:
        path = self.root / str(uuid4())
        path.mkdir()
        if with_file:
            (path / "constancia.pdf").write_bytes(b"x" * 100)
        return _aged(path, days_old)

    def test_sweep_removes_orphans_and_reports_freed_space(self):
        old = self._staging(20)
        recent = self._staging(1)

        with patch.object(
            settings, "PAYMENT_PROVIDER_STORAGE_DIR", str(self.root)
        ):
            summary = PaymentProviderStagingCleanup(FakeSession()).run()

        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())
        self.assertEqual(summary["removed_orphan"], 1)
        self.assertEqual(summary["kept"], 1)
        self.assertEqual(summary["freed_bytes"], 100)

    def test_sweep_never_touches_the_archive_directory(self):
        # El archivo permanente vive dentro del staging: si el barrido lo
        # tratara como una carpeta mas, borraria las constancias guardadas.
        archive = self.root / "archive" / "2026" / "09"
        archive.mkdir(parents=True)
        guardada = archive / "constancia.pdf"
        guardada.write_bytes(b"pdf")
        _aged(self.root / "archive", 400)

        with patch.object(
            settings, "PAYMENT_PROVIDER_STORAGE_DIR", str(self.root)
        ):
            summary = PaymentProviderStagingCleanup(FakeSession()).run()

        self.assertTrue(guardada.exists())
        self.assertEqual(summary["scanned"], 0)
        self.assertEqual(summary["removed_total"], 0)

    def test_sweep_on_missing_storage_dir_is_a_noop(self):
        with patch.object(
            settings,
            "PAYMENT_PROVIDER_STORAGE_DIR",
            str(self.root / "no-existe"),
        ):
            summary = PaymentProviderStagingCleanup(FakeSession()).run()

        self.assertEqual(summary["removed_total"], 0)
        self.assertEqual(summary["scanned"], 0)


class ArchiveServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.staging = self.root / str(uuid4())
        self.staging.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _payload(self, name="pago.pdf", content=b"%PDF-1.4 fake"):
        source = self.staging / f"{uuid4()}.pdf"
        source.write_bytes(content)
        return {
            "file_path": str(source),
            "filename": name,
            "content_type": "application/pdf",
        }, source

    def test_archiving_moves_the_file_and_records_the_row(self):
        payload, source = self._payload()
        item_id = uuid4()
        session = FakeSession()

        with patch.object(
            settings, "PAYMENT_PROVIDER_STORAGE_DIR", str(self.root)
        ):
            rows = PaymentProviderArchiveService(session).archive_item_attachments(
                item_id,
                [payload],
            )

        self.assertEqual(len(rows), 1)
        row = rows[0]

        # El original ya no esta en el staging: fue un move, no una copia.
        self.assertFalse(source.exists())
        self.assertTrue(Path(row.file_path).is_file())
        self.assertEqual(Path(row.file_path).read_bytes(), b"%PDF-1.4 fake")

        self.assertEqual(row.entity_type, PAYMENT_PROVIDER_EMAIL_ENTITY_TYPE)
        self.assertEqual(row.entity_id, item_id)
        self.assertEqual(row.file_name, "pago.pdf")
        self.assertEqual(row.file_extension, "pdf")
        self.assertEqual(row.storage_type, "disk")
        self.assertEqual(row.file_size, len(b"%PDF-1.4 fake"))
        self.assertEqual(session.added, rows)

    def test_archive_path_is_sharded_by_year_and_month(self):
        payload, _ = self._payload()

        now = datetime.now(timezone.utc)

        with patch.object(
            settings, "PAYMENT_PROVIDER_STORAGE_DIR", str(self.root)
        ):
            [row] = PaymentProviderArchiveService(
                FakeSession()
            ).archive_item_attachments(uuid4(), [payload])
            expected = (
                Path(settings.payment_provider_archive_dir) / f"{now.year:04d}"
            )
        self.assertTrue(
            str(Path(row.file_path)).startswith(str(expected)),
            f"{row.file_path} no empieza en {expected}",
        )
        self.assertEqual(Path(row.file_path).parent.name, f"{now.month:02d}")

    def test_missing_source_is_skipped_not_an_error(self):
        # Un reintento puede encontrar el PDF ya archivado.
        payload = {
            "file_path": str(self.staging / "ya-no-esta.pdf"),
            "filename": "pago.pdf",
        }

        with patch.object(
            settings, "PAYMENT_PROVIDER_STORAGE_DIR", str(self.root)
        ):
            rows = PaymentProviderArchiveService(
                FakeSession()
            ).archive_item_attachments(uuid4(), [payload])

        self.assertEqual(rows, [])

    def test_archive_dir_defaults_inside_the_storage_volume(self):
        with patch.object(
            settings, "PAYMENT_PROVIDER_STORAGE_DIR", "/data/staging"
        ):
            archive = Path(settings.payment_provider_archive_dir)

        self.assertEqual(archive.parent, Path("/data/staging"))
        self.assertEqual(archive.name, "archive")


if __name__ == "__main__":
    unittest.main()
