"""
tests/test_events.py
Admin event CRUD + participant event listing.
Covers: create, get, update, delete, publish toggle, participant view.
"""

import pytest
from app import create_app
from extensions import db as _db, bcrypt
from models.user import User
from models.event import Event


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

EVENT_PAYLOAD = {
    "title":      "Tech Summit 2025",
    "venue":      "Main Hall",
    "capacity":   200,
    "event_date": "2025-12-01",
    "start_time": "09:00",
    "end_time":   "17:00",
    "description": "Annual tech event",
}


def make_user(app, role="participant", email="user@test.com"):
    pw   = bcrypt.generate_password_hash("Pass123").decode()
    user = User(name="Test", email=email, password=pw, role=role)
    _db.session.add(user)
    _db.session.commit()
    _db.session.refresh(user)
    return user.id


def get_token(client, email, password="Pass123"):
    res = client.post("/api/auth/login",
                      json={"email": email, "password": password},
                      content_type="application/json")
    return res.get_json()["data"]["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_event(client, token, payload=None):
    return client.post("/api/admin/events",
                       json=payload or EVENT_PAYLOAD,
                       headers=auth(token),
                       content_type="application/json")


# ──────────────────────────────────────────
# Admin event CRUD
# ──────────────────────────────────────────

class TestAdminEvents:

    def setup_admin(self, app, client):
        make_user(app, role="admin", email="admin@test.com")
        return get_token(client, "admin@test.com")

    def test_create_event_success(self, app, client):
        token = self.setup_admin(app, client)
        res   = create_event(client, token)
        assert res.status_code == 201
        body = res.get_json()
        assert body["success"] is True
        assert body["data"]["title"] == EVENT_PAYLOAD["title"]

    def test_create_event_missing_field(self, app, client):
        token   = self.setup_admin(app, client)
        payload = {**EVENT_PAYLOAD}
        del payload["venue"]
        res = create_event(client, token, payload)
        assert res.status_code == 400

    def test_create_event_non_admin_forbidden(self, app, client):
        make_user(app, role="participant", email="p@test.com")
        token = get_token(client, "p@test.com")
        res   = create_event(client, token)
        assert res.status_code == 403

    def test_get_all_events(self, app, client):
        token = self.setup_admin(app, client)
        create_event(client, token)
        res = client.get("/api/admin/events", headers=auth(token))
        assert res.status_code == 200
        assert isinstance(res.get_json()["data"], list)
        assert len(res.get_json()["data"]) >= 1

    def test_get_single_event(self, app, client):
        token    = self.setup_admin(app, client)
        event_id = create_event(client, token).get_json()["data"]["id"]
        res      = client.get(f"/api/admin/events/{event_id}", headers=auth(token))
        assert res.status_code == 200
        assert res.get_json()["data"]["id"] == event_id

    def test_get_nonexistent_event(self, app, client):
        token = self.setup_admin(app, client)
        res   = client.get("/api/admin/events/99999", headers=auth(token))
        assert res.status_code == 404

    def test_update_event(self, app, client):
        token    = self.setup_admin(app, client)
        event_id = create_event(client, token).get_json()["data"]["id"]
        res      = client.put(
            f"/api/admin/events/{event_id}",
            json={"title": "Updated Title"},
            headers=auth(token),
            content_type="application/json"
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["title"] == "Updated Title"

    def test_delete_event(self, app, client):
        token    = self.setup_admin(app, client)
        event_id = create_event(client, token).get_json()["data"]["id"]
        res      = client.delete(f"/api/admin/events/{event_id}", headers=auth(token))
        assert res.status_code == 200
        # Verify it's gone
        get_res = client.get(f"/api/admin/events/{event_id}", headers=auth(token))
        assert get_res.status_code == 404

    def test_publish_toggle(self, app, client):
        token    = self.setup_admin(app, client)
        event_id = create_event(client, token).get_json()["data"]["id"]
        # Publish
        res = client.put(f"/api/admin/events/{event_id}/publish", headers=auth(token))
        assert res.status_code == 200
        assert res.get_json()["data"]["is_published"] is True
        # Unpublish
        res2 = client.put(f"/api/admin/events/{event_id}/publish", headers=auth(token))
        assert res2.get_json()["data"]["is_published"] is False

    def test_mark_complete(self, app, client):
        token    = self.setup_admin(app, client)
        event_id = create_event(client, token).get_json()["data"]["id"]
        res      = client.put(f"/api/admin/events/{event_id}/complete", headers=auth(token))
        assert res.status_code == 200
        assert res.get_json()["data"]["is_completed"] is True


# ──────────────────────────────────────────
# Participant event listing
# ──────────────────────────────────────────

class TestParticipantEvents:

    def _setup(self, app, client):
        # Admin creates + publishes event
        make_user(app, role="admin", email="admin@test.com")
        admin_token = get_token(client, "admin@test.com")
        event_id    = create_event(client, admin_token).get_json()["data"]["id"]
        client.put(f"/api/admin/events/{event_id}/publish", headers=auth(admin_token))

        # Participant
        make_user(app, role="participant", email="part@test.com")
        part_token = get_token(client, "part@test.com")
        return part_token, event_id

    def test_participant_sees_published_events(self, app, client):
        token, _ = self._setup(app, client)
        res      = client.get("/api/participant/events", headers=auth(token))
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert len(data) >= 1
        assert all(e["is_published"] for e in data)

    def test_participant_gets_single_published_event(self, app, client):
        token, event_id = self._setup(app, client)
        res = client.get(f"/api/participant/events/{event_id}", headers=auth(token))
        assert res.status_code == 200

    def test_participant_cannot_access_unpublished_event(self, app, client):
        make_user(app, role="admin", email="admin@test.com")
        admin_token = get_token(client, "admin@test.com")
        event_id    = create_event(client, admin_token).get_json()["data"]["id"]
        # NOT published

        make_user(app, role="participant", email="part@test.com")
        token = get_token(client, "part@test.com")
        res   = client.get(f"/api/participant/events/{event_id}", headers=auth(token))
        assert res.status_code == 404