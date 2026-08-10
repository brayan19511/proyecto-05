# Permiso unico para consultar estado del sistema y analitica de logs/jobs.
# Es informacion sensible de operacion, por eso va detras de un permiso propio.
OBSERVABILITY_VIEW_PERMISSION = "observability.view"

# Estados posibles de un componente en el chequeo de salud.
STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"

# Prioridad para calcular el estado global (el peor gana).
STATUS_SEVERITY = {
    STATUS_OK: 0,
    STATUS_DEGRADED: 1,
    STATUS_DOWN: 2,
}

# Ruta de login para clasificar intentos de autenticacion en la auditoria.
LOGIN_PATH_SUFFIX = "/auth/login"
