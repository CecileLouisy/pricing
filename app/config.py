"""Application configuration — typed environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "local"
    DATABASE_URL: str = "sqlite:///./pricing.db"
    ADMIN_TOKEN: str = "change-me-in-production"
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
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
