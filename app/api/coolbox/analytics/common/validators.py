"""Reusable validation and normalization for analytics services."""

from datetime import date

from fastapi import HTTPException, status


def validate_date_range(fecha_inicio: date, fecha_fin: date) -> None:
    if fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inicio no puede ser mayor a la fecha fin.",
        )


def validate_limit(limit: int, maximum: int) -> None:
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El limite debe ser mayor a cero.",
        )
    if limit > maximum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El limite maximo permitido es {maximum}.",
        )


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    normalized = [value.strip() for value in values if value and value.strip()]
    # De-duplicate bind parameters while preserving filter order.
    return list(dict.fromkeys(normalized)) or None
