# Despliegue Azure con ETL local

## Objetivo

El servidor remoto ejecuta los servicios de consulta: backend, PostgreSQL y,
opcionalmente, pgAdmin. La sincronizacion ETL contra RadioShack se ejecuta desde
tu PC local porque ahi tienes el acceso remoto y las credenciales del origen.
Con este flujo no publicas credenciales sensibles de RadioShack en Azure ni en
Docker Hub.

## Flujo operativo

1. La PC local consulta RadioShack y carga datos a PostgreSQL remoto.
2. El backend remoto consume PostgreSQL y expone APIs para frontend, Power BI o Excel.
3. El frontend remoto consume el backend por HTTPS/Nginx.
4. PostgreSQL remoto se expone solo si es necesario, idealmente por SSH tunnel,
   VPN o firewall de IP permitida.

## Variables importantes

- `BACKEND_IMAGE`: imagen publicada en Docker Hub, por ejemplo `usuario/radioshack-backend:latest`.
- `DB_BIND_ADDRESS`: usa `127.0.0.1` si te conectaras por SSH tunnel; usa `0.0.0.0` solo si Azure Firewall/NSG limita las IPs permitidas.
- `DB_RASH_*`: solo deben existir en el entorno local que ejecuta el ETL, no en el servidor remoto.

## Levantar servicios en produccion

Sin pgAdmin:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Con pgAdmin:

```bash
docker compose -f docker-compose.prod.yml --profile admin up -d
```

Aplicar migraciones:

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## Migraciones en Docker local

Si levantaste PostgreSQL con `docker compose up -d`, ejecuta Alembic dentro del
contenedor de la API para usar el host interno `db-postgres` y SSL desactivado:

```bash
docker compose exec api alembic upgrade head
```

Si prefieres ejecutar Alembic desde tu PC contra el puerto publicado de Docker,
tu `.env` local debe usar:

```dotenv
DB_HOST=localhost
DB_SSL_MODE=disable
```

## Analisis de productos

Los endpoints analiticos de productos filtran por `dim_producto.tipo = 'PRO'`.
El ETL normaliza `TI_ITEM` a mayusculas antes de guardarlo para que PostgreSQL
pueda usar el indice `ix_dim_producto_tipo` sin aplicar funciones sobre la
columna en cada consulta.
