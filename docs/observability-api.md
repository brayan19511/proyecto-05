# API de Observabilidad — Contrato para Frontend

Módulo para el dashboard de **estado del sistema** y **analítica de logs/jobs**.

- **Prefijo base:** `/api/observability`
- **Autenticación:** todas las rutas requieren un usuario autenticado con el permiso **`observability.view`** (el rol `Observabilidad` y `Admin` ya lo tienen). Enviar el token como en el resto de la API (header `Authorization`).
- **Errores comunes:**
  - `401` sin autenticación · `403` sin el permiso.
  - `422` parámetros inválidos (p. ej. `date_from >= date_to`, o rango mayor a 92 días).
  - `404` en el detalle si el `log_id` no existe.

## Convenciones

- **Fechas** (`date_from`, `date_to`): ISO 8601 (`2026-08-20T00:00:00Z`). Si se omiten, el rango por defecto es **las últimas 24 h**. Sin zona horaria se interpretan como **UTC**. Rango máximo permitido: **92 días**.
- **Paginación** (endpoints de listado): `limit` (1–200, default 50) y `offset` (default 0). La respuesta paginada tiene esta forma:

```json
{ "items": [ ... ], "total": 1234, "limit": 50, "offset": 0, "has_more": true }
```

---

## 1. Estado del sistema

`GET /api/observability/status`

Chequeo en vivo de las dependencias (bases de datos, workers, colas, SMTP, scheduler). Sin parámetros.

```json
{
  "status": "degraded",
  "checked_at": "2026-08-20T14:03:11Z",
  "components": [
    { "component": "postgres",        "status": "ok",       "latency_ms": 3.2,  "detail": null },
    { "component": "db_icg",          "status": "ok",       "latency_ms": 41.7, "detail": null },
    { "component": "db_cic",          "status": "ok",       "latency_ms": 38.0, "detail": null },
    { "component": "db_sap",          "status": "down",     "latency_ms": 5001, "detail": "timeout o error: ..." },
    { "component": "db_ofisis_ecomm", "status": "ok",       "latency_ms": 22.4, "detail": null },
    { "component": "celery_workers",  "status": "ok",       "latency_ms": 120,  "detail": "3 worker(s): heavy@..., light@... | colas: light=0, heavy=2, email=0" },
    { "component": "smtp",            "status": "ok",       "latency_ms": 88.1, "detail": null },
    { "component": "scheduler",       "status": "degraded", "latency_ms": null, "detail": "ultima ejecucion: ...; tareas con fallos: 1" }
  ]
}
```

- `status` (global y por componente): `"ok"` | `"degraded"` | `"down"`. El global es el peor de los componentes.
- Sugerencia UI: semáforo verde/amarillo/rojo por componente + un indicador global arriba.

---

## 2. Resumen de logs (tarjetas del dashboard)

`GET /api/observability/logs/summary?date_from=&date_to=`

```json
{
  "date_from": "2026-08-19T14:00:00Z",
  "date_to": "2026-08-20T14:00:00Z",
  "total_requests": 8421,
  "by_level":        [ { "label": "INFO", "count": 8100 }, { "label": "WARNING", "count": 280 }, { "label": "ERROR", "count": 41 } ],
  "by_status_class": [ { "label": "2xx", "count": 8100 }, { "label": "4xx", "count": 280 }, { "label": "5xx", "count": 41 } ],
  "error_rate": 0.0049,
  "avg_duration_ms": 84.31,
  "p95_duration_ms": 512.7,
  "top_users": [ { "label": "2f3c...uuid", "count": 1203 }, { "label": "9a11...uuid", "count": 640 } ],
  "top_ips":   [ { "label": "10.0.0.5", "count": 2100 }, { "label": "10.0.0.9", "count": 980 } ]
}
```

- `error_rate`: proporción de 5xx sobre el total (0..1). Mostrar como %.
- `top_users`/`top_ips`: los 5 más recurrentes. En `top_users`, `label` es el **`user_id` (UUID)** — para mostrar nombre/correo, resolverlo con el módulo de usuarios.

---

## 3. Endpoints más usados / más lentos / con más errores

`GET /api/observability/logs/endpoints?date_from=&date_to=&sort=&limit=`

- `sort`: `requests` (default) | `avg_duration` | `errors`.
- `limit`: 1–100 (default 20).

```json
{
  "date_from": "...", "date_to": "...",
  "items": [
    { "method": "GET", "path": "/api/finance/...", "requests": 1200, "avg_duration_ms": 45.2, "p95_duration_ms": 210.0, "error_count": 3 }
  ]
}
```

---

## 4. Errores (listado)

`GET /api/observability/logs/errors?date_from=&date_to=&limit=&offset=`

Preset de peticiones con nivel `ERROR`/`CRITICAL` o status `>= 500`. Respuesta paginada de `items`:

```json
{ "id": "uuid", "trace_id": "uuid", "level": "ERROR", "method": "POST", "path": "/api/...", "status_code": 500,
  "error_message": "...", "duration_ms": 91.0, "user_id": "uuid|null", "created_at": "..." }
```

> Para navegar **warnings** o filtrar con más criterios, usar el endpoint genérico **#7**. Para el detalle completo de cualquier fila, usar **#8** con su `id`.

---

## 5. Login — conteo agregado (tarjeta)

`GET /api/observability/logs/auth?date_from=&date_to=`

```json
{ "date_from": "...", "date_to": "...", "total_attempts": 340, "succeeded": 300, "failed": 40, "distinct_users": 52, "distinct_ips": 61 }
```

## 6. Login — eventos (quién y a qué hora)

`GET /api/observability/logs/auth/events?date_from=&date_to=&limit=&offset=`

Listado paginado de cada intento de login:

```json
{ "id": "uuid", "user_id": "uuid|null", "ip_address": "10.0.0.5", "user_agent": "Mozilla/5.0 ...",
  "status_code": 200, "succeeded": true, "created_at": "2026-08-20T09:12:03Z" }
```

---

## 7. Navegar TODAS las peticiones (con filtros)

`GET /api/observability/logs?...`

Parámetros (todos opcionales salvo paginación con defaults):

| Param | Valores | Descripción |
|---|---|---|
| `date_from`, `date_to` | ISO 8601 | Rango (default últimas 24 h) |
| `level` | `INFO`\|`WARNING`\|`ERROR`\|`CRITICAL` | Filtra por nivel |
| `status_class` | `2xx`\|`3xx`\|`4xx`\|`5xx` | Filtra por clase de estado |
| `method` | `GET`, `POST`, ... | Método HTTP |
| `path_contains` | texto | Coincidencia parcial en la ruta |
| `user_id` | UUID | Peticiones de un usuario |
| `min_duration_ms` | número | Solo peticiones que tardaron ≥ ese valor (para hallar lentas) |
| `limit`, `offset` | | Paginación |

Respuesta paginada de `items` (fila para la tabla):

```json
{ "id": "uuid", "trace_id": "uuid", "level": "INFO", "method": "GET", "path": "/api/...",
  "status_code": 200, "duration_ms": 42.0, "user_id": "uuid|null", "ip_address": "10.0.0.5",
  "error_message": null, "created_at": "..." }
```

Uso típico: esta es la **tabla principal**; cada fila es cliqueable y abre el detalle (#8) con su `id`.

---

## 8. Detalle de una petición (click en una fila)

`GET /api/observability/logs/{log_id}`

Devuelve todo lo capturado de esa petición: qué envió, qué respondimos, status, headers, y **los pasos** internos que ejecutó.

```json
{
  "id": "uuid",
  "trace_id": "uuid",
  "method": "POST",
  "path": "/api/finance/...",
  "status_code": 200,
  "level": "INFO",
  "duration_ms": 133.5,
  "user_id": "uuid|null",
  "ip_address": "10.0.0.5",
  "user_agent": "Mozilla/5.0 ...",
  "environment": "prod",
  "started_at": "...", "finished_at": "...", "created_at": "...",

  "request_headers": { "content-type": "application/json", "authorization": "[REDACTED]" },
  "query_params":    { "account": "97" },
  "request_body":    { "campo": "valor", "password": "[REDACTED]" },
  "response_body":   { "id": "...", "estado": "OK" },
  "response_size_bytes": 512,
  "error_message": null,
  "error_stack": null,

  "steps": [
    { "step_order": 1, "step_name": "VALIDATE_TOKEN", "status": "INFO", "message": "ok", "duration_ms": 2.1, "extra_data": null },
    { "step_order": 2, "step_name": "SAVE",           "status": "INFO", "message": null, "duration_ms": 88.0, "extra_data": { "rows": 3 } }
  ]
}
```

Notas importantes:
- Los campos sensibles llegan ya **redactados** (`authorization`, `cookie`, `password`, `token`, `secret`, base64 de archivos, etc.). Es esperado: mostrarlos tal cual.
- Los `response_body` de rutas `/api/attendance`, `/api/jobs` y `/api/sap` llegan como `{ "info": "[REDACTED]" }` por política del backend.
- `steps` puede venir vacío si la petición no registró pasos.

---

## 9. Rendimiento de Jobs / Workers

`GET /api/observability/jobs/summary?date_from=&date_to=`

```json
{
  "date_from": "...", "date_to": "...",
  "total_jobs": 210,
  "failure_rate": 0.019,
  "by_type": [
    { "job_type": "LEDGER_SYNC_DELTA", "total": 120, "succeeded": 118, "failed": 2, "running": 0, "avg_duration_seconds": 12.4 }
  ]
}
```

---

## Layout sugerido del dashboard

| Sección | Endpoint |
|---|---|
| Semáforo de salud | `#1 /status` |
| Tarjetas (total, error %, p95, top usuarios/IPs) | `#2 /logs/summary` |
| Top endpoints (usados / lentos / con errores) | `#3 /logs/endpoints` |
| Tabla principal de peticiones (con filtros) → click abre detalle | `#7 /logs` → `#8 /logs/{id}` |
| Vista rápida de errores | `#4 /logs/errors` → `#8` |
| Login: tarjeta + tabla de eventos | `#5 /logs/auth` + `#6 /logs/auth/events` |
| Jobs/Workers | `#9 /jobs/summary` |

## Fuera de alcance de esta API (aclaración)

- El **detalle del envío de correos** (destinatario, asunto, resultado SMTP) **no** está aquí: los correos se envían en un worker, no son peticiones HTTP. Ese detalle vive en la API de **jobs**: `GET /api/jobs/{id}` y `GET /api/jobs/{id}/items`. Esta API sí registra la petición HTTP que *encoló* el correo.
