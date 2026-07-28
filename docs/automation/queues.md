# Jobs y tareas en cola

El proyecto usa Celery con RabbitMQ para procesos que no deben mantener una
peticion HTTP abierta: operaciones masivas SAP, exportaciones grandes y futuras
notificaciones. PostgreSQL conserva el estado funcional para la API y la UX.

## Responsabilidad de cada componente

```text
Frontend -> FastAPI -> PostgreSQL (jobs, lotes, items)
                    -> RabbitMQ -> worker light/heavy/email
```

- FastAPI valida, registra el job y responde `202 Accepted`.
- RabbitMQ transporta mensajes pequenos con el UUID del lote.
- Celery consume, reintenta y limita la concurrencia.
- PostgreSQL es la fuente de verdad para progreso, resultados y propietario.
- Las credenciales enviadas por el usuario se guardan cifradas; nunca viajan
  en texto plano ni forman parte del mensaje de RabbitMQ.

## Las tres tablas

### `jobs.jobs`

Representa la operacion solicitada por el usuario. Usa `AuditMixin`, por lo que
`created_by` permite construir "Mis tareas" y `updated_by` registra quien
solicito una cancelacion. Contiene tipo, estado, parametros sanitizados,
contadores agregados, fechas e idempotencia.

No almacena los 35,000 documentos en un JSON. Solo guarda el resumen necesario
para listar y mostrar progreso rapidamente.

### `jobs.job_batches`

Representa la unidad entregada a un worker. Un job de 35,000 documentos con
lotes de 200 crea 175 batches. Cada batch guarda su `celery_task_id`, intentos,
heartbeat y contadores.

La tabla permite reintentar una parte pequena y cancelar sin repetir todo el
trabajo. No usa `AuditMixin`: es una unidad tecnica y su usuario se obtiene por
la relacion con `jobs`.

### `jobs.job_items`

Representa un documento individual. Guarda referencia, estado, intentos,
codigo externo y error seguro. Permite mostrar errores paginados y reintentar
solo los elementos fallidos.

Tampoco usa `AuditMixin`; duplicar el usuario en decenas de miles de filas no
agrega informacion.

## API

Crear una operacion SAP:

```http
POST /api/sap/services
Idempotency-Key: cierre-2026-07-empresa-1
```

```json
{
  "user": "usuario-sap",
  "password": "password-sap",
  "database": "SBO_COMPANY",
  "entidad": "Invoices",
  "action": "Cancel",
  "documentos": [1001, 1002, 1003]
}
```

La respuesta incluye `job_id`, estado, progreso y lotes. `user` y `password`
se cifran antes de guardar el job y no aparecen en respuestas ni auditoria.

```text
GET  /api/jobs?mine=true
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/items?status=FAILED
POST /api/jobs/{job_id}/cancel
POST /api/jobs/{job_id}/retry
```

`retry` vuelve a publicar un job con error de despacho. Para un job procesado,
crea un job hijo que contiene solamente los items fallidos.

### Libro mayor programado

Para tareas externas puedes usar el endpoint async directamente:

```http
POST /api/libro-mayor/sync-delta-all-async?batch_size=1
X-API-Key: <api-key>
Idempotency-Key: libro-mayor-delta-all-20260728-04
```

En Windows Task Scheduler puedes usar un solo comando, sin crear scripts
adicionales:

```powershell
-ExecutionPolicy Bypass -Command "$slot = Get-Date -Format 'yyyyMMdd-HH'; Invoke-RestMethod -Uri 'http://192.168.32.25:8080/api/libro-mayor/sync-delta-all-async?batch_size=1' -Method Post -Headers @{'X-API-Key'='<api-key>'; 'Idempotency-Key'=\"libro-mayor-delta-all-$slot\"}"
```

La clave idempotente cambia por hora (`yyyyMMdd-HH`). Asi una
ejecucion de las 04:00 y otra de las 08:00 pueden crear jobs distintos, pero un
reintento de la misma hora reutiliza el job ya creado.

Si quieres que la aplicacion administre el calendario, crea una tarea
programada. Por ahora este flujo esta pensado para libro mayor:

```http
POST /api/scheduled-jobs
```

```json
{
  "name": "Libro mayor delta laboral",
  "job_type": "LEDGER_SYNC_DELTA",
  "enabled": true,
  "schedule_kind": "WINDOW_INTERVAL",
  "schedule_config": {
    "weekdays": [0, 1, 2, 3, 4],
    "start_time": "08:00",
    "end_time": "18:00",
    "minutes": 240
  },
  "parameters": {"operation": "sync_delta_all"},
  "batch_size": 1,
  "timezone": "America/Lima"
}
```

Tipos de calendario soportados:

- `DAILY`: una o varias horas fijas, por ejemplo `{"times": ["12:00"]}`.
- `INTERVAL_MINUTES`: cada cierto numero de minutos, por ejemplo `{"minutes": 135}` para cada 2h15.
- `WINDOW_INTERVAL`: dentro de una ventana, por ejemplo lunes a viernes de 08:00 a 18:00 cada 4 horas.

El servicio `scheduler` despierta cada minuto, busca tareas vencidas en
`jobs.scheduled_jobs` y crea ejecuciones reales en `jobs.jobs`. El historico se
consulta con:

```http
GET /api/jobs?scheduled_job_id=<id>
```

## Cancelacion

La cancelacion es cooperativa:

1. La API cambia el estado a `CANCEL_REQUESTED`.
2. Revoca mensajes pendientes sin terminar procesos.
3. El worker activo revisa el estado antes de cada documento.
4. Los documentos ya procesados no se revierten en SAP.
5. Los restantes pasan a `CANCELLED`.

No usar terminacion forzada del proceso como flujo funcional. Puede interrumpir
una llamada SAP cuyo resultado ya no sea verificable.

## Reintentos e idempotencia

- Errores de conexion se reintentan hasta tres veces con backoff.
- Errores funcionales SAP quedan en el item y no detienen el lote.
- Un item interrumpido durante una llamada queda como resultado incierto para
  revision, evitando repetir automaticamente una operacion posiblemente hecha.
- `Idempotency-Key` evita crear dos jobs por doble clic o reenvio HTTP.

## Colas y escalado

Las colas se separan por perfil operativo:

- `light`: tareas cortas o de bajo volumen.
- `heavy`: SAP, libro mayor por rango y reprocesos largos.
- `email`: correos y adjuntos, aislados de las cargas pesadas.

El dispatcher decide la cola antes de publicar el mensaje. Por ejemplo, un
delta de libro mayor de un solo dia/cuenta puede ir a `light`; rangos mayores y
reprocesos van a `heavy`.

Para escalar, aumenta replicas o concurrencia solo despues de medir la capacidad
de SAP y PostgreSQL. No combines varios workers con concurrencias altas sin
calcular la concurrencia total.

Los workers tienen limites Docker configurables (`WORKER_HEAVY_MEM_LIMIT`,
`WORKER_HEAVY_CPUS`, etc.) y Celery recicla procesos con
`CELERY_WORKER_MAX_TASKS_PER_CHILD` y
`CELERY_WORKER_MAX_MEMORY_PER_CHILD_KB`. Si una tarea consume demasiada memoria,
Docker puede terminar solo ese worker; la API queda separada y el job conserva
estado para revision/reintento.

Si el mismo lote cae repetidamente por memoria, no conviene reintentarlo sin
cambios. Baja la concurrencia o `batch_size`, divide mas el rango, o aumenta
`WORKER_HEAVY_MEM_LIMIT` segun el servidor. El objetivo es fallar de forma
aislada y observable, no dejar que el proceso tumbe toda la aplicacion.

## Operacion

```bash
docker compose up -d rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up -d api scheduler worker-light worker-heavy worker-email
docker compose logs -f worker-heavy
```

RabbitMQ Management se publica solamente en desarrollo en el puerto configurado
por `RABBITMQ_MANAGEMENT_PORT`. No exponerlo directamente en produccion.

`JOB_CREDENTIALS_KEY` puede contener una clave Fernet dedicada. Si queda vacia,
la aplicacion deriva una clave de `JWT_SECRET`. Cambiar cualquiera de esas claves
invalida las credenciales de jobs que todavia no hayan terminado.
