"""
tests/test_auth.py
Auth route + AuthService tests.
Covers: register, login, /me, duplicate email, wrong password.
"""

import pytest
from app import create_app
from extensions import db as _db
from models.user import User


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

VALID_USER = {
    "name":     "Test User",
    "email":    "test@example.com",
    "password": "Password123",
    "phone":    "9999999999",
}


def register(client, data=None):
    return client.post("/api/auth/register",
                       json=data or VALID_USER,
                       content_type="application/json")


def login(client, email="test@example.com", password="Password123"):
    return client.post("/api/auth/login",
                       json={"email": email, "password": password},
                       content_type="application/json")


# ──────────────────────────────────────────
# Register tests
# ──────────────────────────────────────────

class TestRegister:

    def test_register_success(self, client):
        res = register(client)
        assert res.status_code == 201
        body = res.get_json()
        assert body["success"] is True
        assert body["data"]["email"] == VALID_USER["email"]
        assert body["data"]["role"]  == "participant"

    def test_register_missing_name(self, client):
        data = {**VALID_USER, "name": ""}
        res  = register(client, data)
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_register_missing_email(self, client):
        data = {**VALID_USER, "email": ""}
        res  = register(client, data)
        assert res.status_code == 400

    def test_register_missing_password(self, client):
        data = {**VALID_USER, "password": ""}
        res  = register(client, data)
        assert res.status_code == 400

    def test_register_duplicate_email(self, client):
        register(client)          # first - OK
        res = register(client)    # second - should fail
        assert res.status_code == 400
        assert "already" in res.get_json()["message"].lower()

    def test_register_no_body(self, client):
        res = client.post("/api/auth/register", content_type="application/json")
        assert res.status_code == 400


# ──────────────────────────────────────────
# Login tests
# ──────────────────────────────────────────

class TestLogin:

    def test_login_success(self, client):
        register(client)
        res  = login(client)
        body = res.get_json()
        assert res.status_code == 200
        assert body["success"] is True
        assert "token" in body["data"]
        assert body["data"]["user"]["email"] == VALID_USER["email"]

    def test_login_wrong_password(self, client):
        register(client)
        res = login(client, password="wrongpassword")
        assert res.status_code == 401
        assert res.get_json()["success"] is False

    def test_login_unknown_email(self, client):
        res = login(client, email="ghost@example.com")
        assert res.status_code == 401

    def test_login_missing_email(self, client):
        res = client.post("/api/auth/login",
                          json={"password": "Password123"},
                          content_type="application/json")
        assert res.status_code == 400

    def test_login_no_body(self, client):
        res = client.post("/api/auth/login", content_type="application/json")
        assert res.status_code == 400


# ──────────────────────────────────────────
# /me tests
# ──────────────────────────────────────────

class TestMe:

    def _get_token(self, client):
        register(client)
        res = login(client)
        return res.get_json()["data"]["token"]

    def test_me_success(self, client):
        token = self._get_token(client)
        res   = client.get("/api/auth/me",
                           headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        body = res.get_json()
        assert body["data"]["email"] == VALID_USER["email"]

    def test_me_no_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_bad_token(self, client):
        res = client.get("/api/auth/me",
                         headers={"Authorization": "Bearer bad.token.here"})
        assert res.status_code == 422