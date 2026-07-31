import base64
import hashlib
import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import ValidationError


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Build one process-local cipher without exposing the source secret."""
    if settings.JOB_CREDENTIALS_KEY:
        key = settings.JOB_CREDENTIALS_KEY.encode()
    else:
        # Domain separation avoids using the JWT secret bytes directly.
        digest = hashlib.sha256(
            f"jobs-credentials:{settings.JWT_SECRET}".encode()
        ).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_job_secrets(payload: dict[str, str]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode()
    return _get_fernet().encrypt(serialized).decode()


def decrypt_job_secrets(token: str | None) -> dict[str, str]:
    if not token:
        raise ValidationError("La tarea no contiene credenciales cifradas")
    try:
        decrypted = _get_fernet().decrypt(token.encode())
        return json.loads(decrypted)
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValidationError(
            "No se pudieron recuperar las credenciales de la tarea"
        ) from exc
