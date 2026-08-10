import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.api.observability.constants import (
    STATUS_DEGRADED,
    STATUS_DOWN,
    STATUS_OK,
    STATUS_SEVERITY,
)
from app.api.observability.repository import ObservabilityRepository
from app.api.observability.schemas import ComponentStatus, SystemStatusResponse
from app.core.config import settings
from app.core.db.db_cic import get_cic_engine
from app.core.db.db_icg import get_icg_engine
from app.core.db.db_ofisis import get_ofisis_engine
from app.core.db.db_postgres import engine as postgres_engine
from app.core.db.db_sap import engine_sap
from app.workers.celery_app import celery_app


# Cotas de tiempo para que el endpoint nunca quede colgado.
CHECK_TIMEOUT_SECONDS = 5.0
CELERY_PING_TIMEOUT_SECONDS = 1.5
SMTP_TIMEOUT_SECONDS = 3.0

# Colas declaradas en celery_app.conf.task_routes.
CELERY_QUEUES = ("light", "heavy", "email")


class SystemStatusService:
    """Chequeos de salud en vivo de las dependencias del sistema."""

    def __init__(self, db: Session):
        self.repository = ObservabilityRepository(db)

    def get_status(self) -> SystemStatusResponse:
        # Chequeos de red/DB en paralelo: cada uno abre su propia conexion, no
        # tocan la sesion ORM del request, por eso son seguros en hilos.
        parallel_checks = [
            ("postgres", lambda: self._check_engine("postgres", postgres_engine)),
            ("db_icg", lambda: self._check_engine("db_icg", get_icg_engine())),
            ("db_cic", lambda: self._check_engine("db_cic", get_cic_engine())),
            ("db_sap", lambda: self._check_engine("db_sap", engine_sap)),
            ("db_ofisis_ecomm", self._check_ofisis),
            ("celery_workers", self._check_celery),
            ("smtp", self._check_smtp),
        ]
        components = self._run_parallel(parallel_checks)
        # El scheduler se consulta con la sesion local (fuera del pool).
        components.append(self._check_scheduler())

        overall = self._worst_status(components)
        return SystemStatusResponse(
            status=overall,
            checked_at=datetime.now(timezone.utc),
            components=components,
        )

    # =====================================================
    # EJECUCION ACOTADA
    # =====================================================
    def _run_parallel(self, checks) -> list[ComponentStatus]:
        results: list[ComponentStatus] = []
        with ThreadPoolExecutor(max_workers=len(checks)) as pool:
            futures = [(name, pool.submit(fn)) for name, fn in checks]
            for name, future in futures:
                try:
                    results.append(future.result(timeout=CHECK_TIMEOUT_SECONDS))
                except Exception as exc:
                    results.append(
                        ComponentStatus(
                            component=name,
                            status=STATUS_DOWN,
                            detail=f"timeout o error: {exc}"[:200],
                        )
                    )
        return results

    @staticmethod
    def _worst_status(components: list[ComponentStatus]) -> str:
        if not components:
            return STATUS_OK
        return max(
            (component.status for component in components),
            key=lambda status: STATUS_SEVERITY.get(status, 0),
        )

    # =====================================================
    # CHEQUEOS
    # =====================================================
    def _check_engine(self, name: str, engine: Engine) -> ComponentStatus:
        start = time.perf_counter()
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return ComponentStatus(
                component=name,
                status=STATUS_OK,
                latency_ms=self._elapsed_ms(start),
            )
        except Exception as exc:
            return ComponentStatus(
                component=name,
                status=STATUS_DOWN,
                latency_ms=self._elapsed_ms(start),
                detail=str(exc)[:200],
            )

    def _check_ofisis(self) -> ComponentStatus:
        engine = get_ofisis_engine(settings.DB_OFISIS_ECOMM_DATABASE)
        return self._check_engine("db_ofisis_ecomm", engine)

    def _check_celery(self) -> ComponentStatus:
        start = time.perf_counter()
        try:
            replies = celery_app.control.ping(timeout=CELERY_PING_TIMEOUT_SECONDS)
        except Exception as exc:
            return ComponentStatus(
                component="celery_workers",
                status=STATUS_DOWN,
                latency_ms=self._elapsed_ms(start),
                detail=f"no se pudo consultar el broker: {exc}"[:200],
            )

        workers = [name for reply in replies for name in reply]
        depths = self._queue_depths()
        detail_parts = [f"{len(workers)} worker(s)"]
        if workers:
            detail_parts.append(", ".join(sorted(workers)))
        if depths is not None:
            detail_parts.append(
                "colas: " + ", ".join(f"{q}={n}" for q, n in depths.items())
            )
        detail = " | ".join(detail_parts)

        if not workers:
            # Broker responde pero ningun worker esta conectado: nada se procesa.
            return ComponentStatus(
                component="celery_workers",
                status=STATUS_DOWN,
                latency_ms=self._elapsed_ms(start),
                detail="sin workers conectados",
            )
        return ComponentStatus(
            component="celery_workers",
            status=STATUS_OK,
            latency_ms=self._elapsed_ms(start),
            detail=detail,
        )

    @staticmethod
    def _queue_depths() -> dict[str, int] | None:
        """Profundidad de cada cola (best-effort) via declaracion pasiva.

        Si el broker no soporta la consulta o la cola aun no existe, se omite
        sin romper el chequeo.
        """
        depths: dict[str, int] = {}
        try:
            with celery_app.connection_for_read() as connection:
                for queue_name in CELERY_QUEUES:
                    try:
                        channel = connection.channel()
                        declared = channel.queue_declare(
                            queue=queue_name,
                            passive=True,
                        )
                        depths[queue_name] = declared.message_count
                        channel.close()
                    except Exception:
                        continue
        except Exception:
            return None
        return depths or None

    def _check_smtp(self) -> ComponentStatus:
        if not settings.SMTP_HOST:
            return ComponentStatus(
                component="smtp",
                status=STATUS_DEGRADED,
                detail="SMTP no configurado",
            )
        start = time.perf_counter()
        try:
            # Solo se prueba la conexion TCP; no se envian credenciales.
            with socket.create_connection(
                (settings.SMTP_HOST, settings.SMTP_PORT),
                timeout=SMTP_TIMEOUT_SECONDS,
            ):
                pass
            return ComponentStatus(
                component="smtp",
                status=STATUS_OK,
                latency_ms=self._elapsed_ms(start),
            )
        except Exception as exc:
            return ComponentStatus(
                component="smtp",
                status=STATUS_DOWN,
                latency_ms=self._elapsed_ms(start),
                detail=str(exc)[:200],
            )

    def _check_scheduler(self) -> ComponentStatus:
        try:
            health = self.repository.scheduler_health()
        except Exception as exc:
            return ComponentStatus(
                component="scheduler",
                status=STATUS_DOWN,
                detail=str(exc)[:200],
            )
        failing = health.get("failing") or 0
        last_run_at = health.get("last_run_at")
        detail = f"ultima ejecucion: {last_run_at}; tareas con fallos: {failing}"
        # Se marca degradado si hay tareas programadas fallando; no se infiere
        # "caido" por antiguedad porque una tarea puede no haber vencido aun.
        status = STATUS_DEGRADED if failing else STATUS_OK
        return ComponentStatus(
            component="scheduler",
            status=status,
            detail=detail,
        )

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return round((time.perf_counter() - start) * 1000, 1)
