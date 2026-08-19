"""Schema GraphQL y su router de FastAPI.

Todo el modulo se expone en UN solo endpoint: POST /api/graphql. Abriendo esa
misma URL en el navegador aparece GraphiQL, una interfaz para escribir
consultas y explorar el schema (pestania Docs). Para ejecutar consultas hay que
cargar el token en la pestania de headers de GraphiQL:

    {"Authorization": "Bearer <token>"}

Las dos extensiones son limites de seguridad: sin ellas un cliente podria pedir
`lineas -> articulo -> ...` anidado indefinidamente y tumbar la base.
"""

import strawberry
from strawberry.extensions import MaxTokensLimiter, QueryDepthLimiter
from strawberry.fastapi import GraphQLRouter

from app.api.graphql.context import obtener_contexto
from app.api.graphql.query import Query


# Profundidad maxima de anidamiento. El camino mas largo previsto es
# documentosVenta -> lineas -> articulo -> familia -> descripcion (5 niveles).
PROFUNDIDAD_MAXIMA = 8

# Tope de tamanio de la consulta, para rechazar consultas gigantes.
TOKENS_MAXIMOS = 2000

schema = strawberry.Schema(
    query=Query,
    # Se pasan como fabricas (lambda) y no como instancias: Strawberry crea una
    # extension nueva por request y asi no se comparte estado entre consultas.
    extensions=[
        lambda: QueryDepthLimiter(max_depth=PROFUNDIDAD_MAXIMA),
        lambda: MaxTokensLimiter(max_token_count=TOKENS_MAXIMOS),
    ],
)

graphql_router = GraphQLRouter(
    schema,
    context_getter=obtener_contexto,
    prefix="/graphql",
    tags=["GRAPHQL"],
)
