"""Utilidades compartidas por las tasks de Celery."""

# Mensaje usado cuando un lote supera el tiempo límite (soft time limit).
BATCH_TIMEOUT_MESSAGE = "El lote excedio el tiempo permitido"


def retry_countdown(retries: int, max_seconds: int) -> int:
    """Backoff exponencial (30s, 60s, 120s, ...) con un tope máximo en segundos."""
    return min(30 * (2 ** retries), max_seconds)
