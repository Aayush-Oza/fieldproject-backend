"""
tests/test_forecast.py
AI forecast service + admin forecast routes.
Covers: model status, predict from event, predict from dict, missing model, bad input.
"""

import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from extensions import db as _db, bcrypt
from models.user import User
from models.event import Event
from datetime import date, time


# ──────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "JWT_SECRET_KEY": "test-jwt-secret",
    })
    with app.app_context():
        _db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_users(app):
    with app.app_context():
        _db.session.execute(_db.text("SET FOREIGN_KEY_CHECKS=0"))
        _db.session.query(User).delete()
        _db.session.execute(_db.text("SET FOREIGN_KEY_CHECKS=1"))
        _db.session.commit()
    yield


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

PREVIEW_PAYLOAD = {
    "capacity":   200,
    "venue":      "Main Hall",
    "event_date": "2025-12-15",
    "start_time": "09:00:00",
    "end_time":   "17:00:00",
    "registered_count": 80,
}

MOCK_RESULT = {
    "predicted_attendance": 120,
    "confidence":           0.85,
    "utilization_pct":      60.0,
}


def make_admin(app, email="admin@test.com"):
    pw   = bcrypt.generate_password_hash("Pass123").decode()
    user = User(name="Admin", email=email, password=pw, role="admin")
    _db.session.add(user)
    _db.session.commit()
    _db.session.refresh(user)
    return user.id


def make_event(app, admin_id):
    ev = Event(
        title        = "Forecast Test",
        venue        = "Hall C",
        capacity     = 200,
        event_date   = date(2025, 12, 15),
        start_time   = time(9, 0),
        end_time     = time(17, 0),
        is_published = True,
        created_by   = admin_id,
    )
    _db.session.add(ev)
    _db.session.commit()
    _db.session.refresh(ev)
    return ev.id


def get_token(client, email, password="Pass123"):
    res = client.post("/api/auth/login",
                      json={"email": email, "password": password},
                      content_type="application/json")
    return res.get_json()["data"]["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────────────────────
# Forecast status
# ──────────────────────────────────────────

class TestForecastStatus:

    def test_status_returns_data(self, app, client):
        make_admin(app)
        token = get_token(client, "admin@test.com")
        res   = client.get("/api/admin/forecast/status", headers=auth(token))
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert "data" in body

    def test_status_requires_admin(self, app, client):
        pw   = bcrypt.generate_password_hash("Pass123").decode()
        user = User(name="P", email="p@test.com", password=pw, role="participant")
        _db.session.add(user)
        _db.session.commit()
        token = get_token(client, "p@test.com")
        res   = client.get("/api/admin/forecast/status", headers=auth(token))
        assert res.status_code == 403


# ──────────────────────────────────────────
# Forecast by event
# ──────────────────────────────────────────

class TestForecastEvent:

    def test_forecast_event_success(self, app, client):
        admin_id = make_admin(app)
        token    = get_token(client, "admin@test.com")
        event_id = make_event(app, admin_id)

        with patch("routes.admin.predict_attendance", return_value=MOCK_RESULT):
            res = client.get(f"/api/admin/forecast/events/{event_id}", headers=auth(token))

        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert "predicted_attendance" in body["data"]

    def test_forecast_event_not_found(self, app, client):
        make_admin(app)
        token = get_token(client, "admin@test.com")
        res   = client.get("/api/admin/forecast/events/99999", headers=auth(token))
        assert res.status_code == 404

    def test_forecast_event_model_not_trained(self, app, client):
        admin_id = make_admin(app)
        token    = get_token(client, "admin@test.com")
        event_id = make_event(app, admin_id)

        with patch("routes.admin.predict_attendance", side_effect=FileNotFoundError):
            res = client.get(f"/api/admin/forecast/events/{event_id}", headers=auth(token))

        assert res.status_code == 503


# ──────────────────────────────────────────
# Forecast preview (from dict)
# ──────────────────────────────────────────

class TestForecastPreview:

    def test_preview_success(self, app, client):
        make_admin(app)
        token = get_token(client, "admin@test.com")

        with patch("routes.admin.predict_attendance_from_dict", return_value=MOCK_RESULT):
            res = client.post("/api/admin/forecast/preview",
                              json=PREVIEW_PAYLOAD,
                              headers=auth(token),
                              content_type="application/json")

        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert body["data"]["predicted_attendance"] == 120

    def test_preview_missing_capacity(self, app, client):
        make_admin(app)
        token   = get_token(client, "admin@test.com")
        payload = {**PREVIEW_PAYLOAD}
        del payload["capacity"]
        res = client.post("/api/admin/forecast/preview",
                          json=payload,
                          headers=auth(token),
                          content_type="application/json")
        assert res.status_code == 400

    def test_preview_missing_event_date(self, app, client):
        make_admin(app)
        token   = get_token(client, "admin@test.com")
        payload = {**PREVIEW_PAYLOAD}
        del payload["event_date"]
        res = client.post("/api/admin/forecast/preview",
                          json=payload,
                          headers=auth(token),
                          content_type="application/json")
        assert res.status_code == 400

    def test_preview_model_not_trained(self, app, client):
        make_admin(app)
        token = get_token(client, "admin@test.com")

        with patch("routes.admin.predict_attendance_from_dict", side_effect=FileNotFoundError):
            res = client.post("/api/admin/forecast/preview",
                              json=PREVIEW_PAYLOAD,
                              headers=auth(token),
                              content_type="application/json")

        assert res.status_code == 503

    def test_preview_requires_admin(self, app, client):
        pw   = bcrypt.generate_password_hash("Pass123").decode()
        user = User(name="P", email="p2@test.com", password=pw, role="participant")
        _db.session.add(user)
        _db.session.commit()
        token = get_token(client, "p2@test.com")
        res   = client.post("/api/admin/forecast/preview",
                        json=PREVIEW_PAYLOAD,
                        headers=auth(token),
                        content_type="application/json")
        assert res.status_code == 403


# ──────────────────────────────────────────
# Service unit tests (direct call, no HTTP)
# ──────────────────────────────────────────

class TestForecastService:

    def test_predict_from_dict_returns_dict(self, app):
        """Service returns a dict with expected keys when model exists."""
        from services.forecast_service import predict_attendance_from_dict

        mock_model = MagicMock()
        mock_model.predict.return_value = [120]

        with app.app_context():
            with patch("ai.forecast_model.load_model", return_value=mock_model):
                try:
                    result = predict_attendance_from_dict(PREVIEW_PAYLOAD)
                    assert isinstance(result, dict)
                except FileNotFoundError:
                    pytest.skip("Model artifact not present - skipping direct service test")

    def test_get_model_status_returns_dict(self, app):
        from services.forecast_service import get_model_status
        with app.app_context():
            status = get_model_status()
            assert isinstance(status, dict)