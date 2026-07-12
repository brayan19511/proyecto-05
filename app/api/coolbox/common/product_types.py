"""Reglas comunes para clasificar productos del modelo Coolbox/RadioShack."""

ANALYTICS_PRODUCT_TYPE = "PRO"
DEFAULT_PRODUCT_TYPE = "OTROS"


def normalize_product_type(value, default: str = DEFAULT_PRODUCT_TYPE) -> str:
    """Normaliza TI_ITEM antes de guardarlo para que los filtros usen indices."""
    if value is None:
        return default

    normalized = str(value).strip().upper()
    return normalized or default


def analytics_product_type_filter(alias: str = "p") -> str:
    """Filtro SQL compartido para reportes enfocados solo en productos vendibles."""
    return f"AND {alias}.tipo = :analytics_product_type"


def analytics_product_type_params() -> dict:
    return {"analytics_product_type": ANALYTICS_PRODUCT_TYPE}
