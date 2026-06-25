# Automatizacion y tareas en cola

## GitHub Actions

El repositorio incluye dos workflows:

| Workflow | Evento | Responsabilidad |
| --- | --- | --- |
| `CI` | Push y pull request | Construir la imagen de pruebas, ejecutar tests y validar OpenAPI. |
| `Publish backend image` | Tag `vX.Y.Z` | Construir y publicar la imagen versionada en Docker Hub. |

## Configuracion en GitHub

Crear un environment llamado `production` y registrar:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Usar un access token de Docker Hub, no la contraseña de la cuenta.

Para publicar:

```bash
git tag v2.3.0
git push origin v2.3.0
```

El workflow publica:

- `backend-finance:2.3.0`
- `backend-finance:2.3`
- una etiqueta asociada al commit

El despliegue al servidor se mantiene separado. La imagen puede desplegarse
manualmente con el procedimiento de `docs/example/deploy/README.md`.

## Despliegue automático futuro

Alternativas, en orden recomendado:

1. SSH desde GitHub Actions a un servidor dedicado.
2. Runner self-hosted restringido al environment `production`.
3. Plataforma administrada de contenedores.

El job de despliegue debe:

1. Actualizar la imagen versionada.
2. Ejecutar `docker compose pull`.
3. Ejecutar la migración una sola vez.
4. Ejecutar `docker compose up -d`.
5. Consultar `/health/ready`.
6. Fallar sin ocultar errores.

No almacenar el `.env` productivo dentro de GitHub si el servidor ya lo
administra localmente.

## Tareas en cola

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
