from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from server.models.player import Player
from server.models.question import Question


class GamePhase(str, Enum):
    WAITING = "waiting"
    DRAWING = "drawing"
    ANSWERING = "answering"
    VOTING = "voting"
    REVEALING = "revealing"
    ROUND_END = "round_end"
    GAME_OVER = "game_over"


@dataclass
class Round:
    """Internal model — not serialized to clients via to_dict()."""
    question: Question
    judge_id: str
    fake_answers: dict = field(default_factory=dict)       # player_id → text
    shuffled_answers: list = field(default_factory=list)    # [{text, is_real, player_id}]
    votes: dict = field(default_factory=dict)               # voter_id → answer_index
    scores_awarded: dict = field(default_factory=dict)      # player_id → int
    round_number: int = 0


@dataclass
class Game:
    """Internal model — not serialized to clients via to_dict()."""
    rounds: list[Round] = field(default_factory=list)
    current_round_index: int = -1
    judge_index: int = 0
    phase: GamePhase = GamePhase.WAITING

    @property
    def current_round(self) -> Optional[Round]:
        if 0 <= self.current_round_index < len(self.rounds):
            return self.rounds[self.current_round_index]
        return None


@dataclass
class Room:
    id: str
    players: list[Player] = field(default_factory=list)
    host_id: str = ""
    phase: GamePhase = GamePhase.WAITING
    current_game: Optional[Game] = None

    def get_player(self, player_id: str) -> Optional[Player]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def connected_players(self) -> list[Player]:
        return [p for p in self.players if p.is_connected]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "players": [p.to_dict() for p in self.players],
            "host_id": self.host_id,
            "phase": self.phase.value,
        }
