# Docker y desarrollo local

## Archivos

| Archivo | Uso |
| --- | --- |
| `Dockerfile` | Construye la imagen del backend. |
| `.dockerignore` | Excluye secretos, Git, caches y archivos innecesarios del build. |
| `docker-compose.yml` | Desarrollo local. Construye desde el codigo y monta el repositorio. |
| `docker-compose.prod.yml` | Produccion. Descarga una imagen versionada. |

## Construir y levantar

La primera vez, o cuando cambie `Dockerfile` o `requirements.txt`:

```bash
docker compose up -d --build
```

Tambien puede hacerse en pasos:

```bash
docker compose build api
docker compose up -d
```

Para publicar manualmente una imagen de producción:

```bash
docker build --target production -t brayan1951/backend-finance:vX.Y.Z .
docker push brayan1951/backend-finance:vX.Y.Z
```

El target `test` ejecuta pruebas y no inicia Uvicorn; no debe publicarse como
imagen productiva.

Si solo cambio codigo Python, el volumen `.:/app` permite continuar sin reconstruir.
Reiniciar la API si fuera necesario:

```bash
docker compose restart api
```

## Que hace el Dockerfile

La etapa `builder` instala herramientas de compilacion como `gcc` y
`libpq-dev`. La etapa final copia solamente el entorno Python resultante y
conserva `libpq5`, necesario en tiempo de ejecucion.

La API se ejecuta con el usuario Linux `app` de UID `10001`, no como `root`.
Esto limita el impacto de una vulnerabilidad dentro del contenedor.

La imagen incluye:

- Codigo de `app/`.
- Migraciones de `alembic/`.
- `alembic.ini`.
- Dependencias Python.

No incluye `.env`, `.git`, entorno virtual local ni documentacion.

## Healthchecks

- `/health/live`: confirma que el proceso responde.
- `/health/ready`: confirma que la API puede conectarse a PostgreSQL.

PostgreSQL utiliza `pg_isready`. La API comienza cuando la base se encuentra
saludable.

## PgAdmin

PgAdmin pertenece al profile `tools`, por lo que no arranca normalmente:

```bash
docker compose --profile tools up -d pg-admin
```

No debe exponerse publicamente en produccion. Preferir VPN, tunel SSH o acceso
temporal.

## Reconstruccion limpia

Usar solamente para diagnostico:

```bash
docker compose build --no-cache api
docker compose up -d
```

No eliminar volumenes salvo que se quiera borrar deliberadamente la base:

```bash
docker compose down
```

El siguiente comando elimina datos persistentes y requiere especial cuidado:

```bash
docker compose down -v
```
