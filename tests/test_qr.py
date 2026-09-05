"""
tests/test_qr.py
QR generation + token validation.
Covers: QR image download, cancelled registration, invalid reg, token validation.
"""

import pytest
from app import create_app
from extensions import db as _db, bcrypt
from models.user import User
from models.event import Event
from models.registration import Registration
from services.qr_service import QRService
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


def make_event(app, admin_id):
    ev = Event(
        title        = "QR Test Event",
        venue        = "Hall B",
        capacity     = 50,
        event_date   = date(2025, 11, 1),
        start_time   = time(10, 0),
        end_time     = time(16, 0),
        is_published = True,
        created_by   = admin_id,
    )
    _db.session.add(ev)
    _db.session.commit()
    _db.session.refresh(ev)
    return ev.id


def make_registration(app, user_id, event_id, status="registered"):
    token = str(uuid.uuid4())
    reg   = Registration(
        user_id  = user_id,
        event_id = event_id,
        qr_token = token,
        status   = status
    )
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


# ──────────────────────────────────────────
# Route tests (via HTTP)
# ──────────────────────────────────────────

class TestQRRoute:

    def _setup(self, app, client):
        admin_id = make_user(app, role="admin",       email="admin@test.com")
        part_id  = make_user(app, role="participant", email="part@test.com")
        event_id = make_event(app, admin_id)
        make_registration(app, part_id, event_id)
        tok      = get_token(client, "part@test.com")
        return tok, event_id

    def test_qr_download_returns_image(self, app, client):
        tok, event_id = self._setup(app, client)
        res = client.get(
            f"/api/participant/events/{event_id}/qr",
            headers=auth(tok)
        )
        assert res.status_code == 200
        assert res.content_type == "image/png"
        # PNG magic bytes
        assert res.data[:4] == b"\x89PNG"

    def test_qr_no_registration(self, app, client):
        admin_id = make_user(app, role="admin",       email="admin@test.com")
        part_id  = make_user(app, role="participant", email="part@test.com")
        event_id = make_event(app, admin_id)
        # No registration created
        tok = get_token(client, "part@test.com")
        res = client.get(f"/api/participant/events/{event_id}/qr", headers=auth(tok))
        assert res.status_code == 404

    def test_qr_cancelled_registration(self, app, client):
        admin_id = make_user(app, role="admin",       email="admin@test.com")
        part_id  = make_user(app, role="participant", email="part@test.com")
        event_id = make_event(app, admin_id)
        make_registration(app, part_id, event_id, status="cancelled")
        tok = get_token(client, "part@test.com")
        res = client.get(f"/api/participant/events/{event_id}/qr", headers=auth(tok))
        assert res.status_code == 404

    def test_qr_requires_auth(self, client):
        res = client.get("/api/participant/events/1/qr")
        assert res.status_code == 401


# ──────────────────────────────────────────
# Service unit tests
# ──────────────────────────────────────────

class TestQRService:

    def test_generate_qr_success(self, app):
        with app.app_context():
            admin_id = make_user(app, role="admin",       email="admin2@test.com")
            part_id  = make_user(app, role="participant", email="part2@test.com")
            event_id = make_event(app, admin_id)
            make_registration(app, part_id, event_id)

            buf, err = QRService.generate_qr(part_id, event_id)
            assert err is None
            assert buf is not None
            assert buf.read(4) == b"\x89PNG"

    def test_generate_qr_no_registration(self, app):
        with app.app_context():
            admin_id = make_user(app, role="admin",       email="admin3@test.com")
            part_id  = make_user(app, role="participant", email="part3@test.com")
            event_id = make_event(app, admin_id)
            # No registration

            buf, err = QRService.generate_qr(part_id, event_id)
            assert buf is None
            assert err is not None

    def test_validate_token_success(self, app):
        with app.app_context():
            admin_id  = make_user(app, role="admin",       email="admin4@test.com")
            part_id   = make_user(app, role="participant", email="part4@test.com")
            event_id  = make_event(app, admin_id)
            qr_token  = make_registration(app, part_id, event_id)

            reg, err = QRService.validate_token(qr_token)
            assert err is None
            assert reg is not None
            assert reg.qr_token == qr_token

    def test_validate_token_invalid(self, app):
        with app.app_context():
            reg, err = QRService.validate_token("not-a-real-token")
            assert reg is None
            assert err is not None

    def test_validate_token_cancelled(self, app):
        with app.app_context():
            admin_id = make_user(app, role="admin",       email="admin5@test.com")
            part_id  = make_user(app, role="participant", email="part5@test.com")
            event_id = make_event(app, admin_id)
            token    = make_registration(app, part_id, event_id, status="cancelled")

            reg, err = QRService.validate_token(token)
            assert reg is None
            assert err is not None