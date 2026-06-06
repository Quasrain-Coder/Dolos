from dataclasses import dataclass, field
import uuid
import secrets


@dataclass
class Player:
    nickname: str
    room_id: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    token: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)
    is_host: bool = False
    score: int = 0
    is_connected: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nickname": self.nickname,
            "is_host": self.is_host,
            "score": self.score,
            "is_connected": self.is_connected,
        }
