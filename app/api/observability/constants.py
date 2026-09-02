# Permiso unico para consultar estado del sistema y analitica de logs/jobs.
# Es informacion sensible de operacion, por eso va detras de un permiso propio.
OBSERVABILITY_VIEW_PERMISSION = "observability.view"

# Estados posibles de un componente en el chequeo de salud.
STATUS_OK = "ok"
STATUS_DISABLED = "disabled"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"

# Prioridad para calcular el estado global (el peor gana). "disabled" pesa
# igual que "ok": un modulo apagado a proposito no es una falla y no debe
# poner el semaforo global en rojo.
STATUS_SEVERITY = {
    STATUS_OK: 0,
    STATUS_DISABLED: 0,
    STATUS_DEGRADED: 1,
    STATUS_DOWN: 2,
}

# Que modulo tiene que estar encendido para que valga la pena chequear el
# componente. Lo que no esta aqui se chequea siempre.
COMPONENT_MODULES = {
    "db_sap": "sap",
    "smtp": "email",
    "db_ofisis_ecomm": "sales_channel",
    "db_cic": "attendance",
    "db_icg": "analytics",
}

# Ruta de login para clasificar intentos de autenticacion en la auditoria.
LOGIN_PATH_SUFFIX = "/auth/login"
