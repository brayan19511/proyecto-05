# API clients para Power BI y Excel

## Proposito

Los usuarios interactivos siguen usando JWT. Las integraciones utilizan una
API key independiente, asociada a un usuario y limitada al scope
`analytics.read`.

La base solo guarda un hash SHA-256 y un prefijo de busqueda. El secreto
completo se devuelve al crear o rotar una clave y no puede recuperarse luego.

## Preparacion

Aplicar la migracion y reconciliar los permisos:

```powershell
enviroments\Scripts\alembic.exe upgrade head
enviroments\Scripts\python.exe -m app.scripts.seed
```

El seed agrega `analytics.read` y el rol `Analista`.

## Gestion

Todas las operaciones requieren un JWT:

```text
GET    /api/security/api-clients
POST   /api/security/api-clients
PATCH  /api/security/api-clients/{id}
PUT    /api/security/api-clients/{id}/status
PUT    /api/security/api-clients/{id}/assign
POST   /api/security/api-clients/{id}/rotate
DELETE /api/security/api-clients/{id}
```

Un usuario administra sus claves. Solo Admin puede crear o reasignar una clave
para otro usuario.

Ejemplo de creacion:

```json
{
  "name": "Power BI - Ventas",
  "scopes": ["analytics.read"],
  "expires_at": "2027-06-30T00:00:00Z"
}
```

La respuesta incluye `api_key` una sola vez. La rotacion invalida el secreto
anterior inmediatamente. La revocacion es permanente para ese secreto.

## Consumo

Todas las rutas `/api/analytics/*` aceptan uno de estos encabezados:

```http
Authorization: Bearer <jwt>
```

```http
X-API-Key: rsk_<prefijo>.<secreto>
```

Ejemplo de Power Query:

```powerquery
let
    BaseUrl = "https://api.ejemplo.com",
    ApiKey = ApiKeyParameter,
    Source = Json.Document(
        Web.Contents(
            BaseUrl,
            [
                RelativePath = "api/analytics/ventas/kpis",
                Query = [
                    fecha_inicio = "2026-01-01",
                    fecha_fin = "2026-06-30"
                ],
                Headers = [#"X-API-Key" = ApiKey]
            ]
        )
    )
in
    Source
```

`ApiKeyParameter` debe configurarse como parametro sensible y no escribirse
directamente en consultas compartidas.

## Rendimiento y seguridad

- `last_used_at` se actualiza como maximo cada 15 minutos por clave.
- Los GET analytics no generan auditoria detallada por defecto.
- SQLAlchemy reutiliza conexiones con un pool acotado.
- Los endpoints sincronicos se ejecutan en el threadpool de FastAPI.
- La auditoria redacta `api_key`, tokens y contrasenas.
- Las API keys no autorizan ETL, usuarios, roles ni permisos.

Para volver a auditar cada consulta analytics:

```env
AUDIT_ANALYTICS_REQUESTS=true
```
