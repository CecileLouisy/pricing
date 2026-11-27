"""Application configuration — typed environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ADMIN_TOKEN = "change-me-in-production"

# Shorter secrets are considered unsafe in production (Render generates 32+ characters).
MIN_SECRET_LENGTH = 16


class Settings(BaseSettings):
    ENV: str = "local"
    DATABASE_URL: str = "sqlite:///./pricing.db"
    ADMIN_TOKEN: str = DEFAULT_ADMIN_TOKEN
    # One API key per calling service, sent in the X-API-Key header.
    BOOKING_API_KEY: str = ""
    ACCESS_API_KEY: str = ""
    CORS_ORIGINS: str = "*"
    LOG_LEVEL: str = "INFO"
    # Set automatically by Render to the SHA of the deployed git commit.
    RENDER_GIT_COMMIT: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        # Neon (and most providers) hand out "postgresql://" URLs; SQLAlchemy would
        # then pick psycopg2, which is not installed. Point it at psycopg 3 instead.
        url = self.DATABASE_URL
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def git_commit(self) -> str:
        """Short SHA of the deployed commit, "unknown" outside Render."""
        return self.RENDER_GIT_COMMIT[:7] or "unknown"

    @property
    def api_keys(self) -> dict[str, str]:
        """Calling service name -> API key, for the keys that are configured."""
        keys = {"booking": self.BOOKING_API_KEY, "access": self.ACCESS_API_KEY}
        return {caller: key for caller, key in keys.items() if key}

    def unsafe_secrets(self) -> list[str]:
        """Names of the secrets that are missing, left at their default value or too short."""
        secrets = {
            "ADMIN_TOKEN": self.ADMIN_TOKEN,
            "BOOKING_API_KEY": self.BOOKING_API_KEY,
            "ACCESS_API_KEY": self.ACCESS_API_KEY,
        }
        return [
            name
            for name, value in secrets.items()
            if value == DEFAULT_ADMIN_TOKEN or len(value) < MIN_SECRET_LENGTH
        ]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
