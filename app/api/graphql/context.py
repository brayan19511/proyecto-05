"""Contexto de GraphQL: lo que cada resolver puede usar via `info.context`.

Se arma una vez por request HTTP y contiene tres cosas:

    usuario  -> el usuario autenticado, o None si no mando credenciales
    repo     -> el repositorio de ICG (todo el SQL)
    loaders  -> los DataLoaders del request

Los loaders se crean NUEVOS en cada request a proposito: cachean resultados
mientras viven, y si duraran mas de un request un usuario podria ver datos
cacheados de otro.

Sobre la autenticacion: aqui NO se rechaza al usuario anonimo. Se guarda
`usuario = None` y el permiso se valida por campo (ver permissions.py). Asi el
navegador puede abrir la interfaz GraphiQL en /api/graphql para explorar el
schema, y recien al ejecutar una consulta se exige el token.
"""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.api.graphql.loaders import construir_loaders
from app.api.graphql.repository import IcgGraphRepository
from app.core.db.db_icg import get_db_icg
from app.core.db.db_postgres import get_db
from app.core.security import validate_api_key, validate_jwt_user


PREFIJO_BEARER = "bearer "


def _usuario_del_request(request: Request, db: Session):
    """Devuelve el usuario si el request trae credenciales validas, o None.

    Acepta los dos mecanismos del proyecto: JWT (Authorization: Bearer ...) y
    llave de API (X-API-Key).
    """
    autorizacion = request.headers.get("Authorization", "")
    if autorizacion.lower().startswith(PREFIJO_BEARER):
        token = autorizacion[len(PREFIJO_BEARER) :].strip()
        usuario = validate_jwt_user(token=token, db=db)
        if usuario:
            return usuario

    api_key = request.headers.get("X-API-Key")
    if api_key:
        return validate_api_key(api_key=api_key, db=db)

    return None


async def obtener_contexto(
    request: Request,
    db: Session = Depends(get_db),
    db_icg: Session = Depends(get_db_icg),
) -> dict:
    repo = IcgGraphRepository(db_icg)

    contexto = {
        "usuario": _usuario_del_request(request, db),
        "repo": repo,
        # Columnas extra de ALBVENTALIN pedidas en este request. Las fija el
        # query raiz y las lee el loader de lineas.
        "columnas_linea": [],
    }
    contexto["loaders"] = construir_loaders(repo, contexto)

    return contexto
