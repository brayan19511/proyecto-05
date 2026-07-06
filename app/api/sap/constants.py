import re


# SAP Service Layer entity and action names are path segments, never free URLs.
SAP_RESOURCE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
