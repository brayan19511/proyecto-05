# Tareas en cola

Una cola es recomendable para procesos que duran varios segundos, dependen de
SAP o deben reintentarse sin mantener abierta una petición HTTP.

Primeros candidatos:

1. Sincronización completa o delta del libro mayor.
2. Reprocesamiento de reglas por cuenta o rango.
3. Envío de documentos a SAP.
4. Exportaciones Excel grandes.
5. Procesamiento futuro de documentos y notificaciones.

No se recomienda mover a cola:

- Consultas normales.
- CRUD de master.
- Autenticación.
- Cambios pequeños de provisiones.

## Arquitectura propuesta

```text
Frontend -> FastAPI -> Redis -> Worker
                       |         |
                       |         +-> SAP
                       |         +-> PostgreSQL
                       |
                       +-> estado del trabajo
```

La API responde inmediatamente:

```json
{
  "job_id": "uuid",
  "status": "PENDING"
}
```

El frontend consulta:

```text
GET /api/jobs/{job_id}
```

Estados mínimos:

- `PENDING`
- `RUNNING`
- `SUCCEEDED`
- `FAILED`
- `CANCELLED`

Cada trabajo debe guardar:

- Tipo de operación.
- Usuario que lo creó.
- Parámetros sanitizados.
- Progreso.
- Número de intentos.
- Resultado o mensaje seguro de error.
- Fechas de creación, inicio y finalización.
- Clave de idempotencia.

## Tecnología recomendada

Para este proyecto:

- Redis como broker inicial.
- Dramatiq si se prioriza simplicidad.
- Celery si se necesitan workflows complejos, scheduling y un ecosistema mayor.

La implementación debe comenzar con un solo proceso, por ejemplo la
sincronización delta. Después de validar monitoreo, reintentos e idempotencia se
pueden migrar los demás procesos.
