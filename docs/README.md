# Documentacion del proyecto

## Ruta de aprendizaje

1. [Inicio rapido](getting-started/quick-start.md)
2. [Docker para desarrollo](development/docker.md)
3. [Estructura del proyecto](development/project-structure.md)
4. [Pruebas](development/testing.md)
5. [Base de datos y Alembic](database/alembic.md)
6. [Bases externas SQL Server](database/external-sql-server.md)
7. [Asistencia desde CIC](database/cic-attendance.md)
8. [Despliegue en produccion](deployment/production.md)
9. [Aprender GitHub Actions](automation/github-actions.md)
10. [Workflows del proyecto](automation/workflows.md)
11. [Jobs y tareas en cola](automation/queues.md)

## Estructura

```text
docs/
|-- getting-started/   Primer arranque.
|-- development/       Docker, estructura, pruebas y herramientas.
|-- database/          PostgreSQL, SQLAlchemy y Alembic.
|-- deployment/        Produccion y ejemplo de servidor.
|-- automation/        GitHub Actions, CI/CD y colas.
|-- functional/        Casos de uso e historias funcionales.
`-- resources/         Postman y referencias auxiliares.
```

## Recursos principales

- [Coleccion de Postman](<resources/postman/Proyecto 05.postman_collection.json>)
- [Ejemplo de despliegue](deployment/example/README.md)
- [Casos de uso de autenticacion](functional/auth/use-cases.md)

## Principios

- Los secretos viven en `.env`, nunca en Git ni en la imagen.
- Desarrollo construye desde el repositorio.
- Produccion usa imagenes versionadas.
- Alembic modifica la estructura de PostgreSQL.
- Las migraciones se ejecutan una vez antes de actualizar la API.
- CI valida; publicar y desplegar son etapas separadas.
