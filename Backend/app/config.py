import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(url: str) -> str:
    """Render entrega postgres:// o postgresql://; SQLAlchemy necesita el driver explícito."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí"}


class BaseConfig:
    ENV_NAME = "development"
    DEBUG = False
    TESTING = False

    JSON_SORT_KEYS = False

    # --- Base de datos -------------------------------------------------
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.getenv("DATABASE_URL", ""))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        # Render exige SSL en conexiones externas.
        "connect_args": {"sslmode": os.getenv("DB_SSLMODE", "require")},
    }

        # --- JWT en cookies httpOnly (HU_01, RG-06) ------------------------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    JWT_TOKEN_LOCATION = ["headers", "cookies"]  # headers: solo para pruebas con dev-token
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_ACCESS_COOKIE_NAME = "SISCONNI_access_token"
    JWT_REFRESH_COOKIE_NAME = "SISCONNI_refresh_token"
    JWT_ACCESS_COOKIE_PATH = "/"
    JWT_REFRESH_COOKIE_PATH = "/api/v1/auth"  # el refresh solo viaja a los endpoints de auth
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = True  # doble token: cabecera X-CSRF-TOKEN en POST/PUT/PATCH/DELETE
    JWT_BLOCKLIST_ENABLED = True
    JWT_BLOCKLIST_TOKEN_CHECKS = ["access", "refresh"]

    # --- Redis (jti revocados en logout, HU_04) -----------------------
    REDIS_URL = os.getenv("REDIS_URL", "")

    # --- CORS / frontend ----------------------------------------------
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    # --- Correo --------------------------------------------------------
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool(os.getenv("MAIL_USE_TLS"), True)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME") or None
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or None
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@despacho.com")

    # --- Reglas de negocio ---------------------------------------------
    ACTIVATION_LINK_HOURS = 48  # HU_05
    LOGIN_MAX_ATTEMPTS = 5  # HU_01: fallos consecutivos que bloquean la cuenta
    LOGIN_LOCK_MINUTES = 15  # HU_01: duración del bloqueo


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = True
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "dev-only-secret-change-me"
    JWT_COOKIE_SECURE = False  # http://localhost


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS: dict = {}
    JWT_SECRET_KEY = "test-secret-key-with-enough-length-for-hs256"
    JWT_COOKIE_SECURE = False
    REDIS_URL = ""  # lista de jti en memoria: las pruebas no dependen de Redis
    MAIL_SERVER = "localhost"
    MAIL_SUPPRESS_SEND = True
    FRONTEND_URL = "http://frontend.test"


class ProductionConfig(BaseConfig):
    ENV_NAME = "production"


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.getenv("APP_ENV", "development")
    try:
        return CONFIGS[name]
    except KeyError as exc:
        raise RuntimeError(f"APP_ENV desconocido: {name!r}") from exc