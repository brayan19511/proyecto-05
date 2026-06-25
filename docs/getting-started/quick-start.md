# Inicio rapido

## Requisitos

- Git.
- Docker Desktop o Docker Engine con Docker Compose v2.
- Acceso de red a SAP cuando se utilicen sus integraciones.

No es necesario instalar Python ni PostgreSQL en la maquina si se usa Docker.

## Preparar el proyecto

```bash
git clone https://github.com/brayan19511/proyecto-05.git
cd proyecto-05
```

Crear el archivo de configuracion:

```bash
cp .env.template .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.template .env
```

Completar como minimo:

```dotenv
API_PORT=8000
POSTGRES_USER=finance
POSTGRES_PASSWORD=change-me
POSTGRES_DB=finance
DB_PORT=5432

JWT_SECRET=change-me-with-a-long-random-value
JWT_ALG=HS256
JWT_EXPIRES_MIN=3600

DB_SAP_USER=
DB_SAP_PASSWORD=
DB_SAP_HOST=
DB_SAP_PORT=
SAP_URL=

ENV=dev
PROJECT_NAME=Backend Finance
BACKEND_CORS_ORIGINS=http://localhost:5173
SQL_ECHO=false
```

## Primer arranque

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Crear o verificar datos base:

```bash
curl http://localhost:8000/api/verify/seed
```

Comprobar el servicio:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Documentacion interactiva:

```text
http://localhost:8000/docs
```

## Comandos habituales

```bash
docker compose ps
docker compose logs -f api
docker compose restart api
docker compose down
```

PgAdmin es opcional:

```bash
docker compose --profile tools up -d pg-admin
```
