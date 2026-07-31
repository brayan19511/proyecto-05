# Ejemplo de despliegue

Esta carpeta representa los archivos minimos que necesita el servidor. No
requiere clonar el repositorio ni construir imagenes localmente.

## Preparacion

```bash
cp .env.example .env
chmod 600 .env
```

Completar las imagenes versionadas y todos los secretos. Si el password de
RabbitMQ contiene caracteres especiales, codificarlo para URL dentro de
`CELERY_BROKER_URL`.

RabbitMQ no publica puertos en produccion; solo la API y los workers acceden por
la red privada de Compose.

## Despliegue

```bash
docker compose pull
docker compose --profile operations run --rm migrate
docker compose up -d
docker compose ps
curl -f http://localhost:8080/health/ready
```

La migracion debe ejecutarse antes de actualizar `api`, `scheduler` y los
workers, porque todos esperan las tablas del schema `jobs`.

PgAdmin es opcional y no se publica mediante Nginx:

```bash
docker compose --profile tools up -d pgadmin
```

Para acceder, utilizar una VPN o un tunel SSH temporal.

## Actualizacion

1. Cambiar `BACKEND_IMAGE` o `FRONTEND_IMAGE` en `.env`.
2. Ejecutar nuevamente el procedimiento de despliegue.
3. Conservar la etiqueta anterior para rollback.

La publicacion de imagenes puede automatizarse con GitHub Actions. Consultar
`../../automation/github-actions.md`.

## Seguridad

- No versionar `.env`.
- No reutilizar etiquetas Docker publicadas.
- No exponer RabbitMQ Management directamente.
- Configurar HTTPS en el servidor o balanceador externo.
- Rotar inmediatamente cualquier credencial que haya sido expuesta.
