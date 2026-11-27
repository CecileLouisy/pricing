"""End-to-end integration tests — HTTP + in-file SQLite."""

import os
from uuid import UUID

import pytest

# Force an ephemeral SQLite database before importing the app
os.environ["DATABASE_URL"] = "sqlite:///./test_pricing.db"
os.environ["ADMIN_TOKEN"] = "test-token"

from fastapi.testclient import TestClient  # noqa: E402
from prometheus_client import REGISTRY  # noqa: E402
from sqlalchemy import inspect, text, update  # noqa: E402

from app import __version__  # noqa: E402
from app.adapters.db.engine import Base, SessionLocal, engine, init_db  # noqa: E402
from app.adapters.db.orm_models import RateORM  # noqa: E402
from app.application import use_cases  # noqa: E402
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

    def test_root_identifies_service(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json() == {
            "service": "pricing",
            "version": __version__,
            "commit": "unknown",
            "docs": "/docs",
            "health": "/health",
        }

    def test_root_answers_head_probe(self, client):
        r = client.head("/")
        assert r.status_code == 200
        assert r.content == b""


class TestQuote:
    def test_walk_in_computes_price(self, client):
        r = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 75},
        )
        assert r.status_code == 201
        body = r.json()
        # Seed: standard/walk_in = 3.00 EUR/h, free_period = 60 min
        # (75 - 60) = 15 billable -> 1 quarter -> 0.75 EUR
        assert body["amount_eur"] == "0.75"
        assert body["currency"] == "EUR"
        assert body["breakdown"]["quarters"] == 1
        assert body["grid_version"] == 1

    def test_reserved_computes_price(self, client):
        r = client.post(
            "/quote",
            json={"zone": "xl", "mode": "reserved", "duration_min": 120},
        )
        assert r.status_code == 201
        assert r.json()["amount_eur"] == "8.00"  # 2h x 4.00

    def test_unknown_zone_returns_404(self, client):
        r = client.post(
            "/quote",
            json={"zone": "moon", "mode": "walk_in", "duration_min": 60},
        )
        assert r.status_code == 404
        assert r.json()["code"] == "ZONE_NOT_FOUND"

    def test_invalid_duration_returns_422(self, client):
        r = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 0},
        )
        assert r.status_code == 422  # Pydantic (gt=0) intercepts before domain

    def test_quote_can_be_retrieved(self, client):
        created = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 120},
        ).json()
        r = client.get(f"/quotes/{created['quote_id']}")
        assert r.status_code == 200
        assert r.json()["amount_eur"] == created["amount_eur"]


class TestRates:
    def test_public_list(self, client):
        r = client.get("/rates")
        assert r.status_code == 200
        assert len(r.json()) == 10  # 5 zones x 2 modes

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
        # 1. Emit a quote
        created = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 120},
        ).json()
        old_amount = created["amount_eur"]

        # 2. Admin changes the rate
        client.patch(
            "/rates/standard/walk_in",
            headers={"X-Admin-Token": "test-token"},
            json={"hourly_rate_eur": "99.00"},
        )

        # 3. The old quote keeps its amount and grid reference
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
        assert r.json()["free_period_min"] == 60

    def test_admin_update_free_period(self, client):
        r = client.patch(
            "/settings/free-period",
            headers={"X-Admin-Token": "test-token"},
            json={"free_period_min": 30},
        )
        assert r.status_code == 200
        assert r.json()["free_period_min"] == 30
        assert r.json()["grid_version"] == 2


class TestParkingCategoryCodes:
    def test_seed_uses_parking_category_codes(self, client):
        zones = {r["zone"] for r in client.get("/rates").json()}
        assert zones == {"standard", "handicapped", "electric", "xl", "two_wheels"}

    def test_quote_accepts_uppercase_parking_code(self, client):
        r = client.post(
            "/quote",
            json={"zone": "HANDICAPPED", "mode": "walk_in", "duration_min": 120},
        )
        assert r.status_code == 201
        assert r.json()["breakdown"]["zone"] == "handicapped"

    def test_former_code_is_no_longer_accepted(self, client):
        r = client.post(
            "/quote",
            json={"zone": "disabled", "mode": "walk_in", "duration_min": 120},
        )
        assert r.status_code == 404
        assert r.json()["code"] == "ZONE_NOT_FOUND"

    def test_rates_by_zone_is_case_insensitive(self, client):
        r = client.get("/rates/TWO_WHEELS")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_startup_renames_legacy_zone_in_a_new_grid(self):
        with SessionLocal() as session:
            session.execute(
                update(RateORM).where(RateORM.zone == "handicapped").values(zone="disabled")
            )
            session.commit()

        with TestClient(app) as started:
            grid = started.get("/grids/current").json()
            zones = {r["zone"] for r in grid["rates"]}
            assert grid["version"] == 2
            assert "handicapped" in zones
            assert "disabled" not in zones
            assert started.get("/grids").json()[-1]["version"] == 1


class TestLogging:
    def test_quote_logs_business_event_and_request(self, client, caplog):
        caplog.set_level("INFO")
        r = client.post(
            "/quote",
            json={"zone": "standard", "mode": "walk_in", "duration_min": 75},
        )
        quote_id = r.json()["quote_id"]
        assert f"event=quote_computed quote_id={quote_id}" in caplog.text
        assert "amount_eur=0.75" in caplog.text
        assert "event=http_request method=POST path=/quote status=201" in caplog.text

    def test_grid_publication_is_logged(self, client, caplog):
        caplog.set_level("INFO")
        client.patch(
            "/settings/free-period",
            headers={"X-Admin-Token": "test-token"},
            json={"free_period_min": 30},
        )
        assert "event=grid_published change=free_period_updated version=2" in caplog.text

    def test_domain_error_is_logged_as_warning(self, client, caplog):
        client.post("/quote", json={"zone": "nope", "mode": "walk_in", "duration_min": 30})
        record = next(r for r in caplog.records if "event=domain_error" in r.getMessage())
        assert record.levelname == "WARNING"
        assert "code=ZONE_NOT_FOUND" in record.getMessage()

    def test_failed_admin_auth_is_logged_without_token(self, client, caplog):
        client.patch(
            "/settings/free-period",
            headers={"X-Admin-Token": "wrong-secret"},
            json={"free_period_min": 30},
        )
        assert "event=admin_auth_failed reason=invalid_token" in caplog.text
        assert "wrong-secret" not in caplog.text


class TestCorrelationId:
    HEADER = "X-Correlation-ID"

    def _quote(self, client, headers=None):
        return client.post(
            "/quote",
            headers=headers or {},
            json={"zone": "standard", "mode": "walk_in", "duration_min": 75},
        )

    def test_received_id_is_reused_logged_and_stored(self, client, caplog):
        caplog.set_level("INFO")
        r = self._quote(client, headers={self.HEADER: "booking-42_abc"})
        assert r.status_code == 201
        assert r.headers[self.HEADER] == "booking-42_abc"
        assert r.json()["correlation_id"] == "booking-42_abc"
        # Every log line of the request carries the same ID.
        for event in ("event=quote_computed", "event=http_request"):
            record = next(rec for rec in caplog.records if event in rec.getMessage())
            assert record.correlation_id == "booking-42_abc"
        # Stored with the quote: retrievable later.
        stored = client.get(f"/quotes/{r.json()['quote_id']}").json()
        assert stored["correlation_id"] == "booking-42_abc"

    def test_header_name_is_case_insensitive(self, client):
        r = self._quote(client, headers={"x-correlation-id": "access-7"})
        assert r.headers[self.HEADER] == "access-7"

    def test_id_is_generated_when_missing(self, client):
        r = self._quote(client)
        generated = r.headers[self.HEADER]
        assert UUID(generated)
        assert r.json()["correlation_id"] == generated

    def test_each_request_gets_its_own_generated_id(self, client):
        first = client.get("/health").headers[self.HEADER]
        second = client.get("/health").headers[self.HEADER]
        assert first != second

    def test_invalid_id_is_replaced_and_not_logged(self, client, caplog):
        caplog.set_level("INFO")
        r = self._quote(client, headers={self.HEADER: "bad id with spaces"})
        assert r.status_code == 201
        assert r.headers[self.HEADER] != "bad id with spaces"
        assert UUID(r.headers[self.HEADER])
        assert "event=invalid_correlation_id length=18 action=replaced" in caplog.text
        assert "bad id with spaces" not in caplog.text

    def test_too_long_id_is_replaced(self, client):
        r = self._quote(client, headers={self.HEADER: "a" * 129})
        assert UUID(r.headers[self.HEADER])

    def test_error_responses_carry_the_id(self, client, caplog):
        r = client.post(
            "/quote",
            headers={self.HEADER: "corr-404"},
            json={"zone": "nope", "mode": "walk_in", "duration_min": 30},
        )
        assert r.status_code == 404
        assert r.headers[self.HEADER] == "corr-404"
        record = next(rec for rec in caplog.records if "event=domain_error" in rec.getMessage())
        assert record.correlation_id == "corr-404"

    def test_unexpected_error_log_carries_the_id(self, caplog, monkeypatch):
        def boom(**_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(use_cases, "compute_quote", boom)
        client = TestClient(app, raise_server_exceptions=False)
        r = self._quote(client, headers={self.HEADER: "corr-500"})
        assert r.status_code == 500
        assert r.json() == {"code": "INTERNAL_ERROR", "message": "Internal server error"}
        record = next(rec for rec in caplog.records if "event=unexpected_error" in rec.getMessage())
        assert record.correlation_id == "corr-500"

    def test_column_is_added_to_an_existing_database(self):
        # Simulate a database created before the column existed (e.g. Neon).
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE quote DROP COLUMN correlation_id"))
        init_db()
        columns = {c["name"] for c in inspect(engine).get_columns("quote")}
        assert "correlation_id" in columns


def _sample(name, labels=None):
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


class TestMetrics:
    def test_endpoint_uses_prometheus_text_format(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
        assert "# TYPE pricing_http_requests_total counter" in r.text
        assert f'pricing_build_info{{commit="unknown",version="{__version__}"}} 1.0' in r.text

    def test_quote_increments_business_and_http_metrics(self, client):
        quotes = {"zone": "standard", "mode": "walk_in"}
        http = {"method": "POST", "route": "/quote", "status": "201"}
        quotes_before = _sample("pricing_quotes_computed_total", quotes)
        http_before = _sample("pricing_http_requests_total", http)
        duration_before = _sample(
            "pricing_http_request_duration_seconds_count", {"method": "POST", "route": "/quote"}
        )
        client.post("/quote", json={"zone": "STANDARD", "mode": "walk_in", "duration_min": 75})
        assert _sample("pricing_quotes_computed_total", quotes) == quotes_before + 1
        assert _sample("pricing_http_requests_total", http) == http_before + 1
        assert (
            _sample(
                "pricing_http_request_duration_seconds_count",
                {"method": "POST", "route": "/quote"},
            )
            == duration_before + 1
        )

    def test_route_template_is_used_not_raw_path(self, client):
        created = client.post(
            "/quote", json={"zone": "standard", "mode": "walk_in", "duration_min": 75}
        ).json()
        client.get(f"/quotes/{created['quote_id']}")
        client.get("/v2/pricing/metrics")
        text_out = client.get("/metrics").text
        assert 'route="/quotes/{quote_id}"' in text_out
        assert created["quote_id"] not in text_out
        assert 'route="unmatched",status="404"' in text_out
        assert "/v2/pricing/metrics" not in text_out

    def test_domain_error_is_counted_by_code(self, client):
        labels = {"code": "ZONE_NOT_FOUND"}
        before = _sample("pricing_domain_errors_total", labels)
        client.post("/quote", json={"zone": "nope", "mode": "walk_in", "duration_min": 30})
        assert _sample("pricing_domain_errors_total", labels) == before + 1

    def test_grid_publication_updates_counter_and_active_version(self, client):
        labels = {"change": "free_period_updated"}
        before = _sample("pricing_grid_publications_total", labels)
        client.patch(
            "/settings/free-period",
            headers={"X-Admin-Token": "test-token"},
            json={"free_period_min": 30},
        )
        assert _sample("pricing_grid_publications_total", labels) == before + 1
        assert _sample("pricing_active_grid_version") == 2

    def test_admin_auth_failure_is_counted(self, client):
        labels = {"reason": "invalid_token"}
        before = _sample("pricing_admin_auth_failures_total", labels)
        client.patch(
            "/settings/free-period",
            headers={"X-Admin-Token": "wrong"},
            json={"free_period_min": 30},
        )
        assert _sample("pricing_admin_auth_failures_total", labels) == before + 1

    def test_active_grid_version_is_set_at_startup(self):
        with TestClient(app) as client:
            client.get("/health")
        assert _sample("pricing_active_grid_version") == 1

    def test_scrapes_are_not_logged_at_info(self, client, caplog):
        caplog.set_level("INFO")
        client.get("/metrics")
        assert "path=/metrics" not in caplog.text
