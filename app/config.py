"""Configuration applicative — variables d'environnement typées."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "local"
    DATABASE_URL: str = "sqlite:///./pricing.db"
    ADMIN_TOKEN: str = "change-me-in-production"
    CORS_ORIGINS: str = "*"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
