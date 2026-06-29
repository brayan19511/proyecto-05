# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # 1. Definimos las piezas (Opcionales para que no explote si falta una)
    POSTGRES_USER: Optional[str] = Field(default=None)
    POSTGRES_PASSWORD: Optional[str] = Field(default=None)
    POSTGRES_DB: Optional[str] = Field(default=None)
    DB_HOST: Optional[str] = Field(default="localhost")
    DB_PORT: Optional[int] = Field(default=5432)
    DB_SSL_MODE: str = "require"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    ENV: str = "dev"
    PROJECT_NAME: str = Field(default="Proyecto-rash")

    # 2. La URL completa (Prioridad para la Nube)
    # Si en el .env o en el sistema existe DATABASE_URL, se cargará aquí
    DATABASE_URL: Optional[str] = Field(default=None)

    DB_RASH_USER: Optional[str] = Field(default=None)
    DB_RASH_PASSWORD: Optional[str] = Field(default=None)
    DB_RASH_HOST: Optional[str] = Field(default=None)
    DB_RASH_DB: Optional[str] = Field(default=None)
    DB_RASH_PORT: Optional[str] = Field(default=None)

    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    JWT_EXPIRES_MIN: int = 3600

    # Bootstrap credentials are optional so secrets never live in source code.
    SEED_ADMIN_EMAIL: Optional[str] = None
    SEED_ADMIN_PASSWORD: Optional[str] = None

    # Audit payloads are useful for diagnostics, but must remain bounded.
    AUDIT_BODY_MAX_BYTES: int = 16_384
    AUDIT_ANALYTICS_REQUESTS: bool = False

    @property
    def ASYNC_DATABASE_ICG_URL(self) -> str:
        # Construcción manual para la DB RASH
        return f"mssql+pyodbc://{self.DB_RASH_USER}:{self.DB_RASH_PASSWORD}@{self.DB_RASH_HOST}/{self.DB_RASH_DB}?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"

    # 3. Propiedad de Python pura (Sin computed_field para evitar el AttributeError)
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)

            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

            if "ssl=" not in url and "sslmode=" not in url:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}ssl=require"

            return url

        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.POSTGRES_DB}?sslmode={self.DB_SSL_MODE}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_ignore_empty=True,  # Ignora variables vacías en el .env
    )


settings = Settings()
