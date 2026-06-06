import pytest
from server.managers.room_manager import RoomManager, RoomNotFoundError, RoomInGameError, RoomFullError
from server.models import GamePhase


class TestRoomManager:
    def test_create_room(self):
        rm = RoomManager()
        room, player = rm.create_room("小明")
        assert len(room.id) == 4
        assert player.nickname == "小明"
        assert player.is_host is True
        assert room.phase == GamePhase.WAITING

    def test_join_room(self):
        rm = RoomManager()
        room, host = rm.create_room("房主")
        room2, player = rm.join_room(room.id, "玩家")
        assert len(room2.players) == 2
        assert player.nickname == "玩家"
        assert player.is_host is False

    def test_join_nonexistent_room(self):
        rm = RoomManager()
        with pytest.raises(RoomNotFoundError):
            rm.join_room("XXXX", "小明")

    def test_room_code_case_insensitive(self):
        rm = RoomManager()
        room, _ = rm.create_room("房主")
        found = rm.get_room(room.id.lower())
        assert found is not None

    def test_remove_player_marks_disconnected(self):
        rm = RoomManager()
        room, player = rm.create_room("唯一玩家")
        rm.remove_player(room.id, player.id)
        # Room persists even when all players disconnect
        assert rm.get_room(room.id) is not None
        assert player.is_connected is False

    def test_reconnect_player(self):
        rm = RoomManager()
        room, player = rm.create_room("小明")
        player.is_connected = False
        reconnected = rm.reconnect_player(room.id, player.id, player.token)
        assert reconnected is not None
        assert reconnected.is_connected is True

    def test_reconnect_bad_token(self):
        rm = RoomManager()
        room, player = rm.create_room("小明")
        result = rm.reconnect_player(room.id, player.id, "wrong-token")
        assert result is None

    def test_multiple_rooms_independent(self):
        rm = RoomManager()
        r1, _ = rm.create_room("A")
        r2, _ = rm.create_room("B")
        assert r1.id != r2.id
        assert len(rm._rooms) == 2
