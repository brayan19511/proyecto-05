"""Declarative definitions for the minimum security catalog."""

PERMISSIONS = (
    ("sap.read", "Ver datos de SAP"),
    ("sap.write", "Modificar datos en SAP"),
    ("sap.execute", "Ejecutar operaciones en SAP"),
    ("security.roles.edit", "Editar roles y sus permisos"),
    ("security.users.view", "Ver usuarios y sus perfiles"),
    ("cic.execute", "Ejecutar procesos automaticos CIC"),
    ("coolbox.etl.execute", "Ejecutar procesos ETL de Coolbox"),
    ("analytics.read", "Consultar indicadores y datos analiticos"),
)

ROLES = ("Admin", "Admin SAP", "Analista")

# Keeping this mapping explicit makes future permission changes auditable.
ROLE_PERMISSIONS = {
    "Admin": tuple(code for code, _ in PERMISSIONS),
    "Admin SAP": ("sap.read", "sap.write", "sap.execute"),
    "Analista": ("analytics.read",),
}
