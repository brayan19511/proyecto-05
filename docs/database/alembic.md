# Base de datos y migraciones

PostgreSQL se administra mediante SQLAlchemy y Alembic. No se deben crear o
modificar tablas manualmente en produccion.

## Esquemas actuales

| Esquema | Responsabilidad |
| --- | --- |
| `security` | Usuarios de autenticacion, roles, permisos y API keys. |
| `user` | Informacion personal del usuario. |
| `master` | Empresas, monedas y areas. |
| `finance` | Provisiones, libro mayor, conceptos y reglas. |
| `storage` | Metadata y contenido de adjuntos. |
| `audit` | Trazas y detalle de auditoria. |

La lista se encuentra en `SCHEMAS` dentro de `alembic/env.py`.

## Crear o modificar un modelo

Los modelos deben:

1. Heredar de `Base`.
2. Declarar el esquema.
3. Usar tipos y nulabilidad explicitos.
4. Definir indices para filtros frecuentes.
5. Registrarse mediante el paquete `app.models`.

Ejemplo:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class CostCenter(Base, AuditMixin):
    __tablename__ = "cost_centers"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
    )
```

Exportarlo desde el `__init__.py` de su dominio y desde `app/models/__init__.py`.
Alembic importa ese paquete para construir `Base.metadata`.

## Generar una migracion

Con los contenedores activos:

```bash
docker compose exec api alembic heads
docker compose exec api alembic revision --autogenerate -m "add cost centers"
```

Una migracion autogenerada es un borrador. Antes de aplicarla:

1. Revisar `upgrade()` y `downgrade()`.
2. Confirmar nombres de tabla, esquema, constraints e indices.
3. Revisar que no elimine columnas o tablas accidentalmente.
4. Confirmar que `down_revision` apunte a la cabeza actual.
5. Verificar que exista una sola cabeza:

```bash
docker compose exec api alembic heads
```

## Aplicar migraciones

```bash
docker compose exec api alembic current
docker compose exec api alembic upgrade head
docker compose exec api alembic current
```

Consultar historial:

```bash
docker compose exec api alembic history --verbose
```

## Agregar un nuevo esquema

Ejemplo para el esquema `purchasing`:

1. Añadirlo a `SCHEMAS` en `alembic/env.py`.
2. Declararlo en los modelos:

```python
__table_args__ = {"schema": "purchasing"}
```

3. Crear una migracion.
4. Añadir explicitamente la creación del esquema para que la migracion sea
   autocontenida:

```python
from alembic import op


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "purchasing"')
    # Creacion de tablas...


def downgrade() -> None:
    # Eliminar primero las tablas del esquema.
    op.execute('DROP SCHEMA IF EXISTS "purchasing"')
```

No eliminar el esquema en `downgrade()` si puede contener objetos administrados
por otro sistema.

## Migraciones en produccion

Ejecutar una sola vez antes de reemplazar la API:

```bash
docker compose pull
docker compose run --rm api alembic upgrade head
docker compose up -d
```

No incluir `alembic upgrade head` en el comando de inicio de todas las replicas.

## Cambios destructivos

Para renombrar o eliminar columnas:

- Crear backup.
- Evaluar compatibilidad con la version anterior de la API.
- Separar el cambio en varias versiones cuando sea necesario.
- Migrar datos antes de añadir `NOT NULL`.
- No automatizar `alembic downgrade`.

Un patron seguro es:

1. Añadir columna nueva nullable.
2. Desplegar codigo compatible con ambas columnas.
3. Copiar o transformar datos.
4. Cambiar lecturas a la columna nueva.
5. Eliminar la columna anterior en otro despliegue.

## Problemas comunes

### Alembic no detecta el modelo

Verificar que el modelo se exporte desde `app/models/__init__.py`.

### Multiples heads

No seleccionar una al azar. Revisar las ramas y crear un merge:

```bash
docker compose exec api alembic heads
docker compose exec api alembic merge heads -m "merge migration heads"
```

### Revision inexistente

No borrar `alembic_version` ni usar `stamp` sin investigar. Recuperar el archivo
de migracion faltante desde Git o restaurar la base. `alembic stamp` solo debe
usarse cuando la estructura ya fue verificada manualmente.

### Base nueva

Crear los servicios y aplicar todas las migraciones:

```bash
docker compose up -d db-postgres
docker compose run --rm api alembic upgrade head
```
