from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    SQL_ECHO: bool = False

    ENV: str = "dev"
    PROJECT_NAME: str = "Proyecto-rash"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"

    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    JWT_EXPIRES_MIN: int = 3600

    DB_SAP_HOST: str
    DB_SAP_PORT: str
    DB_SAP_USER: str
    DB_SAP_PASSWORD: str
    SAP_URL: str

    DB_OFISIS_HOST: Optional[str] = None
    DB_OFISIS_PORT: int = 1433
    DB_OFISIS_USER: Optional[str] = None
    DB_OFISIS_PASSWORD: Optional[str] = None
    DB_OFISIS_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_OFISIS_ENCRYPT: bool = False
    DB_OFISIS_TRUST_SERVER_CERTIFICATE: bool = False
    DB_OFISIS_ECOMM_DATABASE: str = "EcommDB"

    @property
    def DATABASE_URL_SAP(self) -> str:
        return (
            f"hana+hdbcli://{self.DB_SAP_USER}:{self.DB_SAP_PASSWORD}"
            f"@{self.DB_SAP_HOST}:{self.DB_SAP_PORT}"
        )

    @property
    def DATABASE_URL_POSTGRES(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
            if "postgresql+psycopg2://" not in url:
                url = url.replace(
                    "postgresql://",
                    "postgresql+psycopg2://",
                    1,
                )
            return url

        required_values = {
            "POSTGRES_USER": self.POSTGRES_USER,
            "POSTGRES_PASSWORD": self.POSTGRES_PASSWORD,
            "POSTGRES_DB": self.POSTGRES_DB,
        }
        missing = [name for name, value in required_values.items() if not value]
        if missing:
            raise ValueError(
                "Falta configurar DATABASE_URL o las variables: "
                f"{', '.join(missing)}"
            )

        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL_POSTGRES

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    def get_ofisis_database_url(self, database: str) -> URL:
        required_values = {
            "DB_OFISIS_HOST": self.DB_OFISIS_HOST,
            "DB_OFISIS_USER": self.DB_OFISIS_USER,
            "DB_OFISIS_PASSWORD": self.DB_OFISIS_PASSWORD,
        }
        missing = [name for name, value in required_values.items() if not value]
        if missing:
            raise ValueError(
                "Falta configurar las variables de Ofisis: "
                f"{', '.join(missing)}"
            )

        if not database.strip():
            raise ValueError("El nombre de la base de datos Ofisis es obligatorio")

        return URL.create(
            "mssql+pyodbc",
            username=self.DB_OFISIS_USER,
            password=self.DB_OFISIS_PASSWORD,
            host=self.DB_OFISIS_HOST,
            port=self.DB_OFISIS_PORT,
            database=database,
            query={
                "driver": self.DB_OFISIS_DRIVER,
                "Encrypt": "yes" if self.DB_OFISIS_ENCRYPT else "no",
                "TrustServerCertificate": (
                    "yes" if self.DB_OFISIS_TRUST_SERVER_CERTIFICATE else "no"
                ),
            },
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
