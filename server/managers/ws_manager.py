from fastapi import WebSocket
import json


class WSManager:
    """Track WebSocket connections per room and broadcast messages."""

    def __init__(self) -> None:
        # room_id → {player_id: WebSocket}
        self._connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, room_id: str, player_id: str, ws: WebSocket) -> None:
        await ws.accept()
        if room_id not in self._connections:
            self._connections[room_id] = {}
        self._connections[room_id][player_id] = ws

    def disconnect(self, room_id: str, player_id: str) -> None:
        if room_id in self._connections:
            self._connections[room_id].pop(player_id, None)
            if not self._connections[room_id]:
                del self._connections[room_id]

    def is_connected(self, room_id: str, player_id: str) -> bool:
        return room_id in self._connections and player_id in self._connections[room_id]

    async def send_to_player(self, room_id: str, player_id: str, data: dict) -> None:
        if room_id in self._connections and player_id in self._connections[room_id]:
            ws = self._connections[room_id][player_id]
            await ws.send_json(data)

    async def broadcast(self, room_id: str, data: dict, exclude: str | None = None) -> None:
        if room_id not in self._connections:
            return
        for pid, ws in list(self._connections[room_id].items()):
            if pid != exclude:
                await ws.send_json(data)

    async def broadcast_to_all(self, room_id: str, data: dict) -> None:
        if room_id not in self._connections:
            return
        for ws in self._connections[room_id].values():
            await ws.send_json(data)
