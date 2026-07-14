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
    SAP_JOB_BATCH_SIZE: int = 200
    SAP_JOB_MAX_DOCUMENTS: int = 50_000
    SAP_JOB_SOFT_TIME_LIMIT: int = 3600
    SAP_JOB_TIME_LIMIT: int = 3900

    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    JOB_CREDENTIALS_KEY: Optional[str] = None

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Rash Peru"
    SMTP_USE_TLS: bool = True
    EMAIL_TEMPLATE_DIR: str = "app/templates/emails"

    DB_OFISIS_HOST: Optional[str] = None
    DB_OFISIS_PORT: int = 1433
    DB_OFISIS_USER: Optional[str] = None
    DB_OFISIS_PASSWORD: Optional[str] = None
    DB_OFISIS_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_OFISIS_ENCRYPT: bool = False
    DB_OFISIS_TRUST_SERVER_CERTIFICATE: bool = False
    DB_OFISIS_ECOMM_DATABASE: str = "EcommDB"

    DB_CIC_HOST: Optional[str] = None
    DB_CIC_PORT: int = 1433
    DB_CIC_USER: Optional[str] = None
    DB_CIC_PASSWORD: Optional[str] = None
    DB_CIC_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_CIC_ENCRYPT: bool = False
    DB_CIC_TRUST_SERVER_CERTIFICATE: bool = False
    DB_CIC_DATABASE: str = "dbcoolbox"

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

    def _build_mssql_url(
        self,
        *,
        system_name: str,
        database: str,
        host: str | None,
        port: int,
        user: str | None,
        password: str | None,
        driver: str,
        encrypt: bool,
        trust_server_certificate: bool,
    ) -> URL:
        required_values = {
            f"DB_{system_name}_HOST": host,
            f"DB_{system_name}_USER": user,
            f"DB_{system_name}_PASSWORD": password,
        }
        missing = [name for name, value in required_values.items() if not value]
        if missing:
            raise ValueError(
                f"Falta configurar las variables de {system_name}: "
                f"{', '.join(missing)}"
            )

        if not database.strip():
            raise ValueError(
                f"El nombre de la base de datos {system_name} es obligatorio"
            )

        return URL.create(
            "mssql+pyodbc",
            username=user,
            password=password,
            host=host,
            port=port,
            database=database,
            query={
                "driver": driver,
                "Encrypt": "yes" if encrypt else "no",
                "TrustServerCertificate": (
                    "yes" if trust_server_certificate else "no"
                ),
            },
        )

    def get_ofisis_database_url(self, database: str) -> URL:
        return self._build_mssql_url(
            system_name="OFISIS",
            database=database,
            host=self.DB_OFISIS_HOST,
            port=self.DB_OFISIS_PORT,
            user=self.DB_OFISIS_USER,
            password=self.DB_OFISIS_PASSWORD,
            driver=self.DB_OFISIS_DRIVER,
            encrypt=self.DB_OFISIS_ENCRYPT,
            trust_server_certificate=self.DB_OFISIS_TRUST_SERVER_CERTIFICATE,
        )

    def get_cic_database_url(self) -> URL:
        return self._build_mssql_url(
            system_name="CIC",
            database=self.DB_CIC_DATABASE,
            host=self.DB_CIC_HOST,
            port=self.DB_CIC_PORT,
            user=self.DB_CIC_USER,
            password=self.DB_CIC_PASSWORD,
            driver=self.DB_CIC_DRIVER,
            encrypt=self.DB_CIC_ENCRYPT,
            trust_server_certificate=self.DB_CIC_TRUST_SERVER_CERTIFICATE,
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
