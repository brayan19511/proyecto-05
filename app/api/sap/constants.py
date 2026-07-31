import re


# En SAP Service Layer, entidad y accion son segmentos de ruta, no URLs libres.
SAP_RESOURCE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
