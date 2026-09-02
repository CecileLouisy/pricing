"""Tests d'intégration bout en bout — HTTP + SQLite en mémoire."""

import os

import pytest

# Force une base SQLite éphémère avant l'import de l'app
os.environ["DATABASE_URL"] = "sqlite:///./test_pricing.db"
os.environ["ADMIN_TOKEN"] = "test-token"

from fastapi.testclient import TestClient  # noqa: E402

from app.adapters.db.engine import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(engine)
    init_db()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "pricing"}


class TestQuote:
    def test_walk_in_computes_price(self, client):
        r = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 75},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["amount_eur"] == "3.00"
        assert body["currency"] == "EUR"
        assert body["breakdown"]["quarters"] == 4
        assert body["grid_version"] == 1

    def test_reserved_computes_price(self, client):
        r = client.post(
            "/quote",
            json={"zone": "xl", "mode": "reserved", "duration_min": 120},
        )
        assert r.status_code == 201
        assert r.json()["amount_eur"] == "8.00"  # 2h × 4.00

    def test_unknown_zone_returns_404(self, client):
        r = client.post(
            "/quote",
            json={"zone": "moon", "mode": "walk_in", "duration_min": 60},
        )
        assert r.status_code == 404
        assert r.json()["code"] == "ZONE_NOT_FOUND"

    def test_invalid_duration_returns_400(self, client):
        r = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 0},
        )
        assert r.status_code == 422  # Pydantic (gt=0) intercepte avant le domaine

    def test_quote_can_be_retrieved(self, client):
        created = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 60},
        ).json()
        r = client.get(f"/quotes/{created['quote_id']}")
        assert r.status_code == 200
        assert r.json()["amount_eur"] == created["amount_eur"]


class TestRates:
    def test_public_list(self, client):
        r = client.get("/rates")
        assert r.status_code == 200
        assert len(r.json()) == 10  # 5 zones × 2 modes

    def test_admin_update_creates_new_grid(self, client):
        r = client.patch(
            "/rates/standard/walk_in",
            headers={"X-Admin-Token": "test-token"},
            json={"hourly_rate_eur": "5.00"},
        )
        assert r.status_code == 200
        assert r.json()["version"] == 2

    def test_update_without_token_returns_401(self, client):
        r = client.patch(
            "/rates/standard/walk_in",
            json={"hourly_rate_eur": "5.00"},
        )
        assert r.status_code == 401

    def test_old_quote_survives_rate_change(self, client):
        # 1. Créer un devis
        created = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 60},
        ).json()
        old_amount = created["amount_eur"]

        # 2. L'admin change le tarif
        client.patch(
            "/rates/standard/walk_in",
            headers={"X-Admin-Token": "test-token"},
            json={"hourly_rate_eur": "99.00"},
        )

        # 3. L'ancien devis conserve son montant et sa référence de grille
        retrieved = client.get(f"/quotes/{created['quote_id']}").json()
        assert retrieved["amount_eur"] == old_amount
        assert retrieved["grid_id"] == created["grid_id"]


class TestGrids:
    def test_list_grids(self, client):
        r = client.get("/grids")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_current_grid_is_v1_initially(self, client):
        r = client.get("/grids/current")
        assert r.status_code == 200
        assert r.json()["version"] == 1


class TestSettings:
    def test_get_free_period(self, client):
        r = client.get("/settings/free-period")
        assert r.status_code == 200
        assert r.json()["free_period_min"] == 15

    def test_admin_update_free_period(self, client):
        r = client.patch(
            "/settings/free-period",
            headers={"X-Admin-Token": "test-token"},
            json={"free_period_min": 30},
        )
        assert r.status_code == 200
        assert r.json()["free_period_min"] == 30
        assert r.json()["grid_version"] == 2
