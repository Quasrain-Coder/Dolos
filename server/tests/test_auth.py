import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.data.db import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


class TestAuth:
    def test_register_success(self):
        resp = client.post("/api/auth/register", json={
            "username": "testplayer",
            "password": "secret123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) == 32
        assert data["user"]["username"] == "testplayer"
        assert data["user"]["total_games"] == 0

    def test_register_duplicate_username(self):
        client.post("/api/auth/register", json={
            "username": "uniqueuser",
            "password": "pass1234",
        })
        resp = client.post("/api/auth/register", json={
            "username": "uniqueuser",
            "password": "pass1234",
        })
        assert resp.status_code == 409

    def test_register_short_username(self):
        resp = client.post("/api/auth/register", json={
            "username": "a",
            "password": "pass1234",
        })
        assert resp.status_code == 400

    def test_register_short_password(self):
        resp = client.post("/api/auth/register", json={
            "username": "validuser",
            "password": "ab",
        })
        assert resp.status_code == 400

    def test_login_success(self):
        client.post("/api/auth/register", json={
            "username": "loginuser",
            "password": "mypassword",
        })
        resp = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "mypassword",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "loginuser"

    def test_login_wrong_password(self):
        client.post("/api/auth/register", json={
            "username": "pwuser",
            "password": "correct",
        })
        resp = client.post("/api/auth/login", json={
            "username": "pwuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = client.post("/api/auth/login", json={
            "username": "nobody",
            "password": "whatever",
        })
        assert resp.status_code == 401

    def test_logout(self):
        resp = client.post("/api/auth/register", json={
            "username": "logoutuser",
            "password": "pass1234",
        })
        token = resp.json()["token"]
        resp2 = client.post("/api/auth/logout", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp2.status_code == 200
        assert resp2.json() == {"ok": True}

        # Token should be invalid after logout
        resp3 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp3.status_code == 401

    def test_get_me_success(self):
        resp = client.post("/api/auth/register", json={
            "username": "meuser",
            "password": "pass1234",
        })
        token = resp.json()["token"]
        resp2 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp2.status_code == 200
        assert resp2.json()["username"] == "meuser"

    def test_get_me_unauthorized(self):
        resp = client.get("/api/users/me")
        assert resp.status_code == 401

    def test_login_empty_username(self):
        resp = client.post("/api/auth/login", json={
            "username": "",
            "password": "something",
        })
        assert resp.status_code == 400

    def test_multi_device_login(self):
        """New login creates a new session; old token remains valid."""
        resp = client.post("/api/auth/register", json={
            "username": "multidevice",
            "password": "pass1234",
        })
        token1 = resp.json()["token"]

        # Login again (different device)
        resp2 = client.post("/api/auth/login", json={
            "username": "multidevice",
            "password": "pass1234",
        })
        token2 = resp2.json()["token"]
        assert token1 != token2

        # Both tokens should work (multi-device)
        resp3 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token1}",
        })
        assert resp3.status_code == 200

        resp4 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token2}",
        })
        assert resp4.status_code == 200

    def test_logout_only_removes_one_session(self):
        """Logout removes only the current session, not all sessions."""
        resp = client.post("/api/auth/register", json={
            "username": "sessionuser",
            "password": "pass1234",
        })
        token1 = resp.json()["token"]

        # Login on another device
        resp2 = client.post("/api/auth/login", json={
            "username": "sessionuser",
            "password": "pass1234",
        })
        token2 = resp2.json()["token"]

        # Logout device 1
        client.post("/api/auth/logout", headers={
            "Authorization": f"Bearer {token1}",
        })

        # Device 1 should be logged out
        resp3 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token1}",
        })
        assert resp3.status_code == 401

        # Device 2 should still work
        resp4 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token2}",
        })
        assert resp4.status_code == 200
