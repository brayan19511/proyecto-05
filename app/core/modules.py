"""Interruptor de modulos: que parte del sistema esta encendida y que no.

Hay dos niveles y el orden importa:

1. ``MODULES_DISABLED`` en el .env. Apagado duro por entorno, para cuando el
   despliegue no tiene las credenciales o la red del modulo (ej. un ambiente
   de pruebas sin SAP). Gana siempre; el panel no lo puede prender.
2. La tabla ``master.modules``. Apagado de negocio: el operador lo cambia en
   caliente desde el panel y no requiere despliegue.

Un modulo que no tenga fila en la tabla se considera ENCENDIDO, para que
agregar un modulo nuevo al catalogo no lo deje muerto si falta correr el seed.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db.db_postgres import SessionLocal, get_db
from app.core.exceptions import ModuleDisabledError


# =====================================================
# CODIGOS
# =====================================================
MODULE_SAP = "sap"
MODULE_EMAIL = "email"
MODULE_PAYMENT_PROVIDER = "payment_provider"
MODULE_LEDGER = "ledger"
MODULE_PROVISIONS = "provisions"
MODULE_SALES_CHANNEL = "sales_channel"
MODULE_ATTENDANCE = "attendance"
MODULE_ANALYTICS = "analytics"
MODULE_ICG_QUERY = "icg_query"


# Catalogo que siembra el seed y que el panel del front lista. El orden es el
# que se muestra en pantalla.
MODULE_CATALOG = [
    {
        "code": MODULE_SAP,
        "name": "Integracion SAP",
        "description": "Envio de documentos y conciliacion contra SAP",
    },
    {
        "code": MODULE_EMAIL,
        "name": "Envio de correos",
        "description": "Salida SMTP de todo el sistema",
    },
    {
        "code": MODULE_PAYMENT_PROVIDER,
        "name": "Pagos a proveedores",
        "description": "Constancias de pago y su envio por correo",
    },
    {
        "code": MODULE_LEDGER,
        "name": "Libro mayor",
        "description": "Sincronizacion y consulta del libro mayor",
    },
    {
        "code": MODULE_PROVISIONS,
        "name": "Provisiones",
        "description": "Registro y aprobacion de provisiones",
    },
    {
        "code": MODULE_SALES_CHANNEL,
        "name": "Canales de venta (Last Miller)",
        "description": "SKUs y promociones de Rappi y PedidosYa",
    },
    {
        "code": MODULE_ATTENDANCE,
        "name": "Asistencia",
        "description": "Consulta de marcas de asistencia",
    },
    {
        "code": MODULE_ANALYTICS,
        "name": "Analitica",
        "description": "Ingesta ICG al data lake y capa silver",
    },
    {
        "code": MODULE_ICG_QUERY,
        "name": "Consultas ICG (GraphQL)",
        "description": "Lectura directa de ICG por GraphQL",
    },
]

MODULE_CODES = frozenset(item["code"] for item in MODULE_CATALOG)
MODULE_NAMES = {item["code"]: item["name"] for item in MODULE_CATALOG}

# Motivo que se reporta cuando el apagado viene del .env y no de la tabla.
ENVIRONMENT_DISABLED_REASON = "Desactivado por configuracion del entorno"


# =====================================================
# CONSULTA
# =====================================================
def module_display_name(code: str) -> str:
    return MODULE_NAMES.get(code, code)


def _read_row(code: str, db: Session):
    from app.models.master.master_model import Module

    return db.query(Module).filter(Module.code == code).first()


def get_disabled_reason(code: str, db: Session | None = None) -> str | None:
    """Motivo por el que el modulo esta apagado, o None si esta encendido."""
    if code in settings.modules_disabled:
        return ENVIRONMENT_DISABLED_REASON

    if db is not None:
        row = _read_row(code, db)
    else:
        # Los llamadores sin sesion (workers, clientes externos) abren la suya.
        with SessionLocal() as own_db:
            row = _read_row(code, own_db)

    # Sin fila = encendido: un modulo nuevo no debe morir por falta de seed.
    if row is None or row.enabled:
        return None

    return row.disabled_reason or "Desactivado por el administrador"


def is_module_enabled(code: str, db: Session | None = None) -> bool:
    return get_disabled_reason(code, db) is None


def enabled_module_codes(db: Session) -> list[str]:
    """Codigos encendidos, en el orden del catalogo. Lo consume /auth/me.

    Resuelve todo con una sola consulta, porque se llama en cada login.
    """
    from app.models.master.master_model import Module

    rows = {row.code: row for row in db.query(Module).all()}

    codes = []
    for item in MODULE_CATALOG:
        code = item["code"]
        if code in settings.modules_disabled:
            continue
        row = rows.get(code)
        if row is None or row.enabled:
            codes.append(code)

    return codes


def require_module(code: str, db: Session | None = None) -> None:
    """Corta la ejecucion si el modulo esta apagado. Se traduce a HTTP 503."""
    reason = get_disabled_reason(code, db)
    if reason is None:
        return

    raise ModuleDisabledError(
        f"El modulo '{module_display_name(code)}' esta desactivado: {reason}",
        code=code,
        reason=reason,
    )


class ModuleEnabled:
    """Dependency de FastAPI: bloquea el router completo si esta apagado.

    Se declara una sola vez en el router raiz de cada modulo, igual que
    ``PermissionChecker`` se declara por endpoint.
    """

    def __init__(self, code: str):
        self.code = code

    def __call__(self, db: Session = Depends(get_db)) -> None:
        require_module(self.code, db)
