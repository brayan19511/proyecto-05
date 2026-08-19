"""Permiso requerido para consultar el schema GraphQL de ICG.

En REST el permiso se valida con `Depends(require_any_permission(...))` en cada
endpoint. En GraphQL hay un solo endpoint (/api/graphql), asi que el permiso se
valida por campo con una clase de permiso de Strawberry.

IMPORTANTE: Strawberry reutiliza la MISMA instancia de esta clase entre
requests, asi que nunca hay que guardar datos del request en `self` (por
ejemplo `self.message = ...`): el valor se filtraria a la consulta siguiente.
Para mensajes que dependen del request se levanta la excepcion directamente.
"""

from typing import Any

import strawberry
from strawberry.exceptions import StrawberryGraphQLError
from strawberry.permission import BasePermission

from app.core.access import has_permission


ICG_QUERY_VIEW_PERMISSION = "graphql.icg.view"


class RequierePermisoIcg(BasePermission):
    """Deja pasar solo si el usuario del request tiene el permiso de ICG.

    Se usa asi en cualquier campo:

        @strawberry.field(permission_classes=[RequierePermisoIcg])
        def mi_campo(self, info: strawberry.Info) -> ...:
            ...

    Cuando no pasa, Strawberry no ejecuta el resolver y responde con el mensaje
    dentro del arreglo "errors".
    """

    message = "No tienes permiso para consultar datos de ICG"

    def has_permission(
        self,
        source: Any,
        info: strawberry.Info,
        **kwargs: Any,
    ) -> bool:
        usuario = info.context.get("usuario")
        if usuario is None:
            raise StrawberryGraphQLError(
                "No autenticado: falta el token o el X-API-Key"
            )

        return has_permission(usuario, ICG_QUERY_VIEW_PERMISSION)
