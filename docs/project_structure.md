# Estructura del proyecto

```text
app/
|-- api/             Routers, schemas, servicios y repositorios por dominio.
|-- core/            Configuracion, seguridad, base de datos y middleware.
|-- models/          Modelos SQLAlchemy agrupados por esquema o dominio.
`-- services/        Servicios transversales, por ejemplo auditoria.

alembic/
|-- versions/        Historial inmutable de migraciones.
`-- env.py           Registro de metadata y configuracion de esquemas.

docs/                Documentacion tecnica, funcional y recursos.
Dockerfile           Definicion de la imagen del backend.
docker-compose.yml   Desarrollo local.
docker-compose.prod.yml
                     Referencia de produccion con imagen versionada.
```

## Convencion por dominio

Un modulo funcional normalmente contiene:

```text
app/api/<dominio>/
|-- <dominio>_router.py
|-- <dominio>_schema.py
|-- <dominio>_service.py
`-- <dominio>_repository.py
```

- Router: HTTP, dependencias, permisos y response models.
- Schema: contratos Pydantic de entrada y salida.
- Service: reglas de negocio y coordinación transaccional.
- Repository: consultas y persistencia SQLAlchemy.
- Model: estructura persistente y relaciones.

## Donde colocar codigo compartido

- `app/core/`: infraestructura global, seguridad, configuración y DB.
- `app/core/access.py`: comprobaciones comunes de roles y permisos.
- `constants.py` dentro del dominio: estados y valores propios del negocio.
- `app/services/`: comportamiento transversal con identidad propia.
- No crear `utils.py` como contenedor general; preferir nombres que indiquen
  responsabilidad.

## Reglas de dependencia

Flujo recomendado:

```text
router -> service -> repository -> model
```

Los modelos no deben importar routers o servicios. Los repositorios no deben
depender de FastAPI. Evitar efectos secundarios en archivos `__init__.py`.

## Añadir un modulo

1. Crear modelos y migración.
2. Crear schemas.
3. Implementar repository y service.
4. Crear router con permisos explícitos.
5. Registrar el router en el agregador del dominio o en `app/main.py`.
6. Añadir seed solo si existen catálogos obligatorios.
7. Documentar rutas y casos de uso.
8. Verificar OpenAPI y migraciones.
