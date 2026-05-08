# Guía de Migraciones con Alembic - Proyecto-05

Esta sección detalla el flujo correcto para gestionar cambios en la base de datos y asegurar que los esquemas personalizados se creen correctamente.

## 1. Definición de Modelos
Todos los modelos deben heredar de la clase `Base` ubicada en `app/core/db_postgres.py`. 

> **Nota:** Si la tabla pertenece a un esquema distinto a `public`, es obligatorio especificarlo en `__table_args__`.

```python
from app.core.db_postgres import Base

class MiModelo(Base):
    __tablename__ = "mi_tabla"
    __table_args__ = {"schema": "security"}  # Esquema personalizado
    # ... definición de columnas
```
## 2. Registro de Modelos en Alembic
Para que el comando `--autogenerate` detecte los cambios, los modelos deben estar importados en `alembic/env.py.`

```python
# Ubicación: alembic/env.py

# 1. Importa la Base
from app.core.db_postgres import Base

# 2. IMPORTA TODOS TUS MODELOS AQUÍ (Vital para que Alembic los vea)
from app.models.security import Auth, Role, Permission, UserRole, RolePermission
from app.models.user import Information

# 3. Asigna la metadata
target_metadata = Base.metadata
```
## 3. Configuración de Esquemas en `env.py`
Dado que Alembic no crea los esquemas automáticamente, debemos forzar su creación en la función `run_migrations_online` dentro de `alembic/env.py:`

```python
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # PASO EXTRA: Crear los esquemas manualmente si no existen
        # "user" va entre comillas dobles por ser palabra reservada en Postgres
        connection.execute(text('CREATE SCHEMA IF NOT EXISTS "security";'))
        connection.execute(text('CREATE SCHEMA IF NOT EXISTS "user";'))
        connection.commit() 

        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```
## 4. Comandos de Consola
### A. Generar nueva migración
Ejecuta esto después de modificar cualquier archivo en la carpeta models/:
```
alembic revision --autogenerate -m "Descripción del cambio"
```
### B. Aplicar cambios a la Base de Datos
```
alembic upgrade head
```
## 5. Solución de Problemas Comunes
Error: "Can't locate revision identified by..."
Si borraste archivos dentro de `alembic/versions/` manualmente, la base de datos quedará desincronizada. Para solucionarlo, resetea el historial de versiones en PostgreSQL:

```
-- Ejecutar en pgAdmin o consola SQL
DROP TABLE IF EXISTS alembic_version;
```