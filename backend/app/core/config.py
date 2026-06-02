"""Application settings loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./moleculab.db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # External APIs (optional)
    GROQ_API_KEY: str = ""
    ADMETLAB_API_KEY: str = ""
    ESMFOLD_API_URL: str = "https://api.esmatlas.com/foldSequence/v1/pdb/"

    # Screening thresholds (Lipinski RO5 + scoring logic from spec)
    LIPINSKI_MW_MAX: float = 500.0
    LIPINSKI_LOGP_MAX: float = 5.0
    LIPINSKI_HBD_MAX: int = 5
    LIPINSKI_HBA_MAX: int = 10
    QED_PASS_THRESHOLD: float = 0.6
    BINDING_ENERGY_STRONG: float = -7.0  # kcal/mol
    ADMET_WEIGHT: float = 0.20
    QED_WEIGHT: float = 0.20
    TOX_WEIGHT: float = 0.20
    BINDING_WEIGHT: float = 0.30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
