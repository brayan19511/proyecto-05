# Ejemplo de despliegue

Esta carpeta representa los archivos mínimos que necesita el servidor. No
requiere clonar el repositorio ni construir imágenes localmente.

## Preparación

```bash
cp .env.example .env
chmod 600 .env
```

Completar las imágenes versionadas y todos los secretos.

## Despliegue

```bash
docker compose pull
docker compose --profile operations run --rm migrate
docker compose up -d
docker compose ps
curl -f http://localhost:8080/health/ready
```

PgAdmin es opcional y no se publica mediante Nginx:

```bash
docker compose --profile tools up -d pgadmin
```

Para acceder, utilizar una VPN o un túnel SSH temporal.

## Actualización

1. Cambiar `BACKEND_IMAGE` o `FRONTEND_IMAGE` en `.env`.
2. Ejecutar nuevamente el procedimiento de despliegue.
3. Conservar la etiqueta anterior para rollback.

La publicación de imágenes puede automatizarse con GitHub Actions. Consultar
`../../automation/github-actions.md`.

## Seguridad

- No versionar `.env`.
- No reutilizar etiquetas Docker publicadas.
- Configurar HTTPS en el servidor o balanceador externo.
- Rotar inmediatamente cualquier credencial que haya sido expuesta.
