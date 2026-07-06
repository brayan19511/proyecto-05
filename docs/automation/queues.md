# Jobs y tareas en cola

El proyecto usa Celery con RabbitMQ para procesos que no deben mantener una
peticion HTTP abierta: operaciones masivas SAP, exportaciones grandes y futuras
notificaciones. PostgreSQL conserva el estado funcional para la API y la UX.

## Responsabilidad de cada componente

```text
Frontend -> FastAPI -> PostgreSQL (jobs, lotes, items)
                    -> RabbitMQ -> worker SAP -> SAP Service Layer
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

El worker actual consume solamente la cola `sap` con concurrencia 4 y prefetch
1. Otros dominios deben usar tareas y colas separadas, por ejemplo `exports` o
`notifications`, aunque compartan imagen e infraestructura.

Para escalar, aumentar replicas o concurrencia solo despues de medir la
capacidad de SAP. No combinar varios procesos Celery con pools de threads
internos sin calcular la concurrencia total.

## Operacion

```bash
docker compose up -d rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up -d api worker-sap
docker compose logs -f worker-sap
```

RabbitMQ Management se publica solamente en desarrollo en el puerto configurado
por `RABBITMQ_MANAGEMENT_PORT`. No exponerlo directamente en produccion.

`JOB_CREDENTIALS_KEY` puede contener una clave Fernet dedicada. Si queda vacia,
la aplicacion deriva una clave de `JWT_SECRET`. Cambiar cualquiera de esas claves
invalida las credenciales de jobs que todavia no hayan terminado.
