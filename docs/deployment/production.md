# Despliegue en produccion

La estrategia recomendada es construir la imagen fuera del servidor, publicarla
con una version y hacer que produccion descargue esa imagen.

## Versionar la imagen

```bash
docker build --target production -t brayan1951/backend-finance:v2.2.0 .
docker push brayan1951/backend-finance:v2.2.0
```

No reutilizar una etiqueta publicada. Cada version debe identificar una imagen
inmutable.

## Carpeta externa del servidor

La carpeta de despliegue puede contener:

```text
finance-deploy/
|-- .env
|-- docker-compose.yml
`-- nginx/
    `-- default.conf
```

No necesita contener el repositorio ni el Dockerfile.

El ejemplo actualizado está en [deployment/example](example/README.md).

## Variables relevantes

```dotenv
BACKEND_IMAGE=brayan1951/backend-finance:v2.2.0
FRONTEND_IMAGE=brayan1951/frontend-finance:v2.2.0

POSTGRES_USER=finance
POSTGRES_PASSWORD=change-me
POSTGRES_DB=finance

JWT_SECRET=change-me
JWT_ALG=HS256
JWT_EXPIRES_MIN=3600

DB_SAP_USER=
DB_SAP_PASSWORD=
DB_SAP_HOST=
DB_SAP_PORT=
SAP_URL=

BACKEND_CORS_ORIGINS=https://finance.example.com
```

Proteger el archivo:

```bash
chmod 600 .env
```

## Procedimiento de despliegue

1. Actualizar `BACKEND_IMAGE` y `FRONTEND_IMAGE`.
2. Descargar imágenes:

```bash
docker compose pull
```

3. Ejecutar migraciones con la imagen nueva:

```bash
docker compose run --rm api alembic upgrade head
```

4. Actualizar servicios:

```bash
docker compose up -d
```

5. Verificar:

```bash
docker compose ps
docker compose logs --tail=100 api
curl -f http://localhost:8080/health/ready
```

6. Limpiar imágenes antiguas únicamente después de validar:

```bash
docker image prune
```

## Rollback

Cambiar `BACKEND_IMAGE` a la version anterior:

```dotenv
BACKEND_IMAGE=brayan1951/backend-finance:v2.1.0
```

Después:

```bash
docker compose pull api
docker compose up -d api
```

El rollback de aplicación no implica downgrade automático de base de datos.
Por eso las migraciones deben ser compatibles con la version anterior cuando
sea posible.

## Backup de PostgreSQL

Ejemplo manual:

```bash
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > finance.dump
```

Los backups deben automatizarse, cifrarse y almacenarse fuera del servidor.

## Seed

El seed verifica y completa datos base de manera idempotente, pero debe ser un
paso explicito:

```bash
curl -f http://localhost:8080/api/verify/seed
```

No reemplaza las migraciones y no debe modificar la estructura de la base.
