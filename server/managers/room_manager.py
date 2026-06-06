import random
import string
from server.models import Player, Room, GamePhase
from server.config import ROOM_CODE_CHARS, ROOM_CODE_LENGTH, MAX_PLAYERS


class RoomNotFoundError(Exception):
    pass


class RoomInGameError(Exception):
    pass


class RoomFullError(Exception):
    pass


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def _generate_code(self) -> str:
        return "".join(random.choices(ROOM_CODE_CHARS, k=ROOM_CODE_LENGTH))

    def create_room(self, nickname: str) -> tuple[Room, Player]:
        # Generate unique room code
        for _ in range(100):
            code = self._generate_code()
            if code not in self._rooms:
                break
        else:
            raise RuntimeError("Failed to generate unique room code")

        player = Player(nickname=nickname)
        room = Room(id=code)
        player.is_host = True
        player.room_id = code
        room.host_id = player.id
        room.players.append(player)
        self._rooms[code] = room
        return room, player

    def join_room(self, room_id: str, nickname: str) -> tuple[Room, Player]:
        room = self._rooms.get(room_id.upper())
        if room is None:
            raise RoomNotFoundError(f"房间 {room_id} 不存在")
        if room.phase != GamePhase.WAITING:
            raise RoomInGameError("游戏已开始，无法加入")
        if len(room.players) >= MAX_PLAYERS:
            raise RoomFullError("房间已满（最多8人）")

        player = Player(nickname=nickname, room_id=room.id)
        room.players.append(player)
        return room, player

    def get_room(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id.upper())

    def remove_player(self, room_id: str, player_id: str) -> Player | None:
        room = self._rooms.get(room_id.upper())
        if room is None:
            return None
        player = room.get_player(player_id)
        if player is None:
            return None
        player.is_connected = False
        # Remove completely only during WAITING phase
        if room.phase == GamePhase.WAITING:
            room.players = [p for p in room.players if p.id != player_id]
        # Clean up empty rooms
        if len(room.players) == 0:
            del self._rooms[room.id]
        return player

    def reconnect_player(self, room_id: str, player_id: str, token: str) -> Player | None:
        room = self._rooms.get(room_id.upper())
        if room is None:
            return None
        player = room.get_player(player_id)
        if player is None or player.token != token:
            return None
        player.is_connected = True
        return player
