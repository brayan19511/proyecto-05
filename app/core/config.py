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
    
    ENV: str = "dev"
    PROJECT_NAME: str = "Proyecto-rash"
    
    # 2. La URL completa (Prioridad para la Nube)
    # Si en el .env o en el sistema existe DATABASE_URL, se cargará aquí
    DATABASE_URL: Optional[str] = Field(default=None)

    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    JWT_EXPIRES_MIN: int = 3600

    # 3. Propiedad de Python pura (Sin computed_field para evitar el AttributeError)
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # Si ya tenemos la URL completa (Caso Nube)
        if self.DATABASE_URL:
            # Corregir prefijo de Render/Heroku si es necesario
            url = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
            # Asegurar que use el driver psycopg2 (o el que prefieras)
            if "postgresql+psycopg2://" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url
        
        # Caso Local: Construcción manual
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore",
        env_ignore_empty=True # Ignora variables vacías en el .env
    )

settings = Settings()