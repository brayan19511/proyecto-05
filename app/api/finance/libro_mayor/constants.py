TEXT_SEARCH_COLUMNS = (
    "proveedor",
    "descripcion",
    "referencia_1",
    "referencia_2",
    "referencia_3",
)

# Únicas cuentas de libro mayor soportadas por el sincronizador.
SUPPORTED_ACCOUNTS = frozenset({"95", "97"})

# Cuentas procesadas por defecto en las tareas masivas (orden de ejecución).
DEFAULT_LEDGER_ACCOUNTS = ("97", "95")
