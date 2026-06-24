# Documentacion del proyecto

Esta carpeta contiene las guias tecnicas y operativas del backend de Finanzas.

## Orden recomendado

1. [Inicio rapido](readme_requeriments.md)
2. [Docker y desarrollo local](readme_docker.md)
3. [Base de datos y Alembic](readme_database.md)
4. [Despliegue en produccion](deployment.md)
5. [Estructura del proyecto](project_structure.md)

## Recursos

- `recursos/Proyecto 05.postman_collection.json`: coleccion de Postman.
- `recursos/docker-compose.prod.yml`: ejemplo de carpeta externa para despliegue.
- `recursos/nginx-default.conf`: proxy minimo para API, healthchecks y frontend.
- `hu/`: historias y criterios funcionales.

## Principios

- Los secretos viven en `.env`; nunca se incluyen en Git ni en la imagen Docker.
- Desarrollo construye la imagen desde el repositorio.
- Produccion descarga una imagen versionada.
- Alembic es la unica fuente para modificar la estructura de PostgreSQL.
- Las migraciones se ejecutan una vez por despliegue, antes de actualizar la API.
- El seed es idempotente, pero se ejecuta como una operacion separada.
