# server/tests/test_ws.py
import pytest
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


class TestHTTPRoutes:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_create_room(self):
        resp = client.post("/api/rooms", json={"nickname": "小明"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["room_id"]) == 4
        assert len(data["player_id"]) == 12
        assert len(data["token"]) == 32

    def test_join_room(self):
        create = client.post("/api/rooms", json={"nickname": "房主"})
        room_id = create.json()["room_id"]
        resp = client.post(f"/api/rooms/{room_id}/join", json={"nickname": "玩家"})
        assert resp.status_code == 200
        assert len(resp.json()["players"]) == 2

    def test_join_nonexistent_room(self):
        resp = client.post("/api/rooms/XXXX/join", json={"nickname": "玩家"})
        assert resp.status_code == 404

    def test_room_info(self):
        create = client.post("/api/rooms", json={"nickname": "房主"})
        room_id = create.json()["room_id"]
        resp = client.get(f"/api/rooms/{room_id}")
        assert resp.status_code == 200
        assert resp.json()["exists"] is True

    def test_create_room_empty_nickname(self):
        resp = client.post("/api/rooms", json={"nickname": ""})
        assert resp.status_code == 400
