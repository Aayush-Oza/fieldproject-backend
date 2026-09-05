"""
tests/test_checkin.py
Check-in flow + duplicate prevention.
Covers: valid check-in, duplicate block, wrong token, wrong event, log endpoint.
"""

import pytest
from app import create_app
from extensions import db as _db, bcrypt
from models.user import User
from models.event import Event
from models.registration import Registration
from models.checkin import Checkin
import uuid
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

def make_user(app, role="participant", email="u@test.com"):
    pw   = bcrypt.generate_password_hash("Pass123").decode()
    user = User(name="Test", email=email, password=pw, role=role)
    _db.session.add(user)
    _db.session.commit()
    _db.session.refresh(user)
    return user.id


def make_event(app, admin_id, published=True):
    ev = Event(
        title        = "Test Event",
        venue        = "Hall A",
        capacity     = 100,
        event_date   = date(2025, 12, 1),
        start_time   = time(9, 0),
        end_time     = time(17, 0),
        is_published = published,
        created_by   = admin_id,
    )
    _db.session.add(ev)
    _db.session.commit()
    _db.session.refresh(ev)
    return ev.id


def make_registration(app, user_id, event_id):
    token = str(uuid.uuid4())
    reg   = Registration(user_id=user_id, event_id=event_id, qr_token=token)
    _db.session.add(reg)
    _db.session.commit()
    _db.session.refresh(reg)
    return reg.qr_token


def get_token(client, email, password="Pass123"):
    res = client.post("/api/auth/login",
                      json={"email": email, "password": password},
                      content_type="application/json")
    return res.get_json()["data"]["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def assign_volunteer(client, admin_token, event_id, volunteer_id):
    client.post(
        f"/api/admin/events/{event_id}/volunteers",
        json={"volunteer_id": volunteer_id},
        headers=auth(admin_token),
        content_type="application/json"
    )


# ──────────────────────────────────────────
# Tests
# ──────────────────────────────────────────

class TestCheckin:

    def _setup(self, app, client):
        admin_id  = make_user(app, role="admin",       email="admin@test.com")
        vol_id    = make_user(app, role="volunteer",   email="vol@test.com")
        part_id   = make_user(app, role="participant", email="part@test.com")

        event_id  = make_event(app, admin_id)
        qr_token  = make_registration(app, part_id, event_id)

        admin_tok = get_token(client, "admin@test.com")
        vol_tok   = get_token(client, "vol@test.com")

        assign_volunteer(client, admin_tok, event_id, vol_id)

        return vol_tok, event_id, qr_token, admin_tok, vol_id

    def test_checkin_success(self, app, client):
        vol_tok, event_id, qr_token, _, _ = self._setup(app, client)
        res = client.post(
            "/api/volunteer/checkin",
            json={"qr_token": qr_token, "event_id": event_id},
            headers=auth(vol_tok),
            content_type="application/json"
        )
        assert res.status_code == 201
        body = res.get_json()
        assert body["success"] is True
        assert body["data"]["event_id"] == event_id

    def test_duplicate_checkin_blocked(self, app, client):
        vol_tok, event_id, qr_token, _, _ = self._setup(app, client)
        # First check-in
        client.post("/api/volunteer/checkin",
                    json={"qr_token": qr_token, "event_id": event_id},
                    headers=auth(vol_tok), content_type="application/json")
        # Second - must be rejected
        res = client.post("/api/volunteer/checkin",
                          json={"qr_token": qr_token, "event_id": event_id},
                          headers=auth(vol_tok), content_type="application/json")
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_checkin_invalid_token(self, app, client):
        vol_tok, event_id, _, _, _ = self._setup(app, client)
        res = client.post(
            "/api/volunteer/checkin",
            json={"qr_token": "totally-fake-token", "event_id": event_id},
            headers=auth(vol_tok),
            content_type="application/json"
        )
        assert res.status_code == 400

    def test_checkin_wrong_event(self, app, client):
        vol_tok, event_id, qr_token, _, _ = self._setup(app, client)
        res = client.post(
            "/api/volunteer/checkin",
            json={"qr_token": qr_token, "event_id": 99999},
            headers=auth(vol_tok),
            content_type="application/json"
        )
        assert res.status_code in (400, 404)

    def test_checkin_missing_fields(self, app, client):
        vol_tok, event_id, _, _, _ = self._setup(app, client)
        res = client.post(
            "/api/volunteer/checkin",
            json={"event_id": event_id},   # missing qr_token
            headers=auth(vol_tok),
            content_type="application/json"
        )
        assert res.status_code == 400

    def test_checkin_requires_volunteer_role(self, app, client):
        _, event_id, qr_token, _, _ = self._setup(app, client)
        # Login as participant - should be rejected
        make_user(app, role="participant", email="part2@test.com")
        part_tok = get_token(client, "part2@test.com")
        res = client.post(
            "/api/volunteer/checkin",
            json={"qr_token": qr_token, "event_id": event_id},
            headers=auth(part_tok),
            content_type="application/json"
        )
        assert res.status_code == 403

    def test_checkin_no_token(self, app, client):
        res = client.post(
            "/api/volunteer/checkin",
            json={"qr_token": "x", "event_id": 1},
            content_type="application/json"
        )
        assert res.status_code == 401

    def test_checkin_log(self, app, client):
        vol_tok, event_id, qr_token, _, _ = self._setup(app, client)
        client.post("/api/volunteer/checkin",
                    json={"qr_token": qr_token, "event_id": event_id},
                    headers=auth(vol_tok), content_type="application/json")

        res = client.get(f"/api/volunteer/checkin/{event_id}/log", headers=auth(vol_tok))
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["event_id"] == event_id

    def test_checkin_log_unassigned_volunteer(self, app, client):
        _, event_id, _, _, _ = self._setup(app, client)
        # New volunteer not assigned to this event
        make_user(app, role="volunteer", email="vol2@test.com")
        tok2 = get_token(client, "vol2@test.com")
        res  = client.get(f"/api/volunteer/checkin/{event_id}/log", headers=auth(tok2))
        assert res.status_code == 403