from logging.config import fileConfig

from sqlalchemy import engine_from_config, text
from sqlalchemy import pool

from alembic import context


# 1. IMPORTA TU CONFIGURACIÓN Y TU BASE
from app.core.config import settings
from app.core.db_postgres import Base  # O de donde venga tu DeclarativeBase

# 2. IMPORTA TODOS TUS MODELOS AQUÍ
# Esto es vital para que Alembic vea las tablas
from app.models.security import Auth, Role, Permission, UserRole, RolePermission
from app.models.user import Information
from app.models.audit import AuditLog


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 3. CONFIGURA LA URL DE LA DB DESDE TU CONFIG.PY
config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None
# 4. DEFINE EL TARGET METADATA
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    # with connectable.connect() as connection:
    #     context.configure(
    #         connection=connection, target_metadata=target_metadata
    #     )

    #     with context.begin_transaction():
    #         context.run_migrations()
    # 5. CONFIGURACIÓN PARA ESQUEMAS (PostgreSQL)
    # Debemos decirles a Alembic que incluya los esquemas 'security' y 'user'
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True, # IMPORTANTE: permite ver múltiples esquemas
        )
        with context.begin_transaction():
            # PASO EXTRA: Crear los esquemas manualmente si no existen
            connection.execute(text('CREATE SCHEMA IF NOT EXISTS "security";'))
            connection.execute(text('CREATE SCHEMA IF NOT EXISTS "user";'))
            connection.execute(text('CREATE SCHEMA IF NOT EXISTS "audit";'))
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
