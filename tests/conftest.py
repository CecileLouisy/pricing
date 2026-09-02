"""Configuration pytest globale — force un env de test avant tout import applicatif."""

import os

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_pricing.db")
os.environ.setdefault("ADMIN_TOKEN", "test-token")
os.environ.setdefault("CORS_ORIGINS", "*")
