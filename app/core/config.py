import unicodedata
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


def normalize_key(value: str) -> str:
    """Minuscula y sin tildes, para que "Contrasena" y "contrasena" empaten."""
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())

    return "".join(char for char in decomposed if not unicodedata.combining(char))


def split_config_list(value: str) -> list[str]:
    """Convierte "a, b ,c" en ["a", "b", "c"], normalizado y sin vacios."""
    return [
        normalize_key(item)
        for item in value.split(",")
        if normalize_key(item)
    ]


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
    CELERY_SCHEDULER_INTERVAL_SECONDS: int = 60
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 50
    CELERY_WORKER_MAX_MEMORY_PER_CHILD_KB: int = 512000
    JOB_CREDENTIALS_KEY: Optional[str] = None

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Rash Peru"
    SMTP_USE_TLS: bool = True
    EMAIL_TEMPLATE_DIR: str = "app/templates/emails"
    PAYMENT_PROVIDER_STORAGE_DIR: str = "var/payment-provider-jobs"
    PAYMENT_PROVIDER_ENABLE_OCR: bool = True
    PAYMENT_PROVIDER_OCR_LANG: str = "spa"
    PAYMENT_PROVIDER_OCR_DPI: int = 250
    PAYMENT_PROVIDER_MIN_TEXT_LENGTH: int = 80

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

    DB_ICG_HOST: Optional[str] = None
    DB_ICG_PORT: int = 1433
    DB_ICG_USER: Optional[str] = None
    DB_ICG_PASSWORD: Optional[str] = None
    DB_ICG_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_ICG_ENCRYPT: bool = False
    DB_ICG_TRUST_SERVER_CERTIFICATE: bool = False
    # Peru (mcoolboxreal) es la base por defecto. Mexico (MCOOLBOXMEXIPROD) esta
    # en el mismo servidor/credenciales; solo cambia el nombre de la base.
    DB_ICG_DATABASE: str = "ICG"
    DB_ICG_DATABASE_MX: Optional[str] = None

    DATA_LAKE_ROOT: str = "var/data-lake"
    ICG_INCREMENTAL_LOOKBACK_DAYS: int = 3

    # =====================================================
    # AUDITORIA: QUE SE ENMASCARA EN LOS DETALLES
    # =====================================================
    # Palabras que marcan un campo como credencial. La coincidencia es por
    # substring y sin tildes, asi que "password" ya cubre new_password,
    # current_password y passwordConfirm; "contrasena" cubre "contraseña".
    # Es lo unico que se enmascara en los cuerpos y query params: cualquier
    # otro campo se guarda tal cual para poder revisar el detalle.
    # Agregar palabras en el .env separadas por coma (ej. sumar "clave").
    AUDIT_SENSITIVE_KEYS: str = (
        "password,contrasena,token,secret,api_key,apikey,credential"
    )

    # Cabeceras que se enmascaran completas (coincidencia exacta, no substring).
    AUDIT_SENSITIVE_HEADERS: str = "authorization,cookie,set-cookie,x-api-key"

    # Campos cuyo contenido se omite por tamano, no por ser sensible
    # (adjuntos en base64 que inflarian la tabla de auditoria).
    AUDIT_FILE_CONTENT_KEYS: str = (
        "file_base64,base64,content_base64,file_content"
    )

    # Prefijos de ruta cuyo cuerpo de respuesta no se guarda. Vacio = se
    # guarda el cuerpo de todas las rutas.
    AUDIT_REDACT_RESPONSE_PATHS: str = ""

    # Tope del cuerpo de respuesta que se guarda. Arriba de esto se registra
    # solo el tamano, para que una respuesta enorme no infle la auditoria.
    AUDIT_MAX_RESPONSE_BODY_BYTES: int = 65_536

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
    def audit_sensitive_keys(self) -> tuple[str, ...]:
        return tuple(split_config_list(self.AUDIT_SENSITIVE_KEYS))

    @property
    def audit_sensitive_headers(self) -> frozenset[str]:
        return frozenset(split_config_list(self.AUDIT_SENSITIVE_HEADERS))

    @property
    def audit_file_content_keys(self) -> frozenset[str]:
        return frozenset(split_config_list(self.AUDIT_FILE_CONTENT_KEYS))

    @property
    def audit_redact_response_paths(self) -> tuple[str, ...]:
        # Las rutas no se normalizan como las llaves: se respeta el path tal
        # cual, solo se limpian espacios y vacios.
        return tuple(
            item.strip()
            for item in self.AUDIT_REDACT_RESPONSE_PATHS.split(",")
            if item.strip()
        )

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

    def icg_database_for_country(self, country_code: str) -> str | None:
        """Base ICG segun el pais del canal (mismo servidor, distinta base).

        Devuelve None para Mexico si no esta configurada, para que el llamador
        omita el enriquecimiento en vez de consultar la base equivocada.
        """
        if country_code == "mx":
            return self.DB_ICG_DATABASE_MX
        return self.DB_ICG_DATABASE

    def get_icg_database_url(self, database: str | None = None) -> URL:
        return self._build_mssql_url(
            system_name="ICG",
            database=database or self.DB_ICG_DATABASE,
            host=self.DB_ICG_HOST,
            port=self.DB_ICG_PORT,
            user=self.DB_ICG_USER,
            password=self.DB_ICG_PASSWORD,
            driver=self.DB_ICG_DRIVER,
            encrypt=self.DB_ICG_ENCRYPT,
            trust_server_certificate=self.DB_ICG_TRUST_SERVER_CERTIFICATE,
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
