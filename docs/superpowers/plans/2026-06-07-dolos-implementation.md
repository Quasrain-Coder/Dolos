# Dolos（瞎掰王）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multiplayer web party game where players bluff fake definitions and vote for the real one.

**Architecture:** Python FastAPI backend with WebSocket for real-time game state, Vue 3 + Vite frontend with Pinia stores. Game state held in server memory, questions persisted in SQLite.

**Tech Stack:** Python 3.11+, FastAPI, SQLite, Vue 3 (Composition API + `<script setup>`), Vite, Pinia, pytest, Vitest

---

## Phase 1 — Backend Skeleton

### Task 1: Python project setup

**Files:**
- Create: `server/requirements.txt`
- Create: `server/config.py`
- Create: `server/main.py`
- Create: `server/__init__.py`

- [ ] **Step 1: Create server directory and requirements**

```bash
mkdir -p server/models server/managers server/routes server/data server/tests
touch server/__init__.py server/models/__init__.py server/managers/__init__.py server/routes/__init__.py server/data/__init__.py server/tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```txt
# server/requirements.txt
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.7.0
```

- [ ] **Step 3: Write config.py**

```python
# server/config.py
ROOM_CODE_LENGTH = 4
ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to avoid confusion
MAX_PLAYERS = 8
MIN_PLAYERS = 4
QUESTION_CATEGORIES = ["成语", "冷知识", "网络梗", "科技术语", "历史"]
```

- [ ] **Step 4: Write main.py skeleton**

```python
# server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Dolos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Create venv, install, verify**

```bash
cd server && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn server.main:app --port 8000 &
sleep 2 && curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
kill %1
```

- [ ] **Step 6: Commit**

```bash
git add server/ && git commit -m "feat: project scaffold with FastAPI skeleton

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Data models

**Files:**
- Create: `server/models/player.py`
- Create: `server/models/question.py`
- Create: `server/models/room.py`
- Create: `server/tests/test_models.py`

- [ ] **Step 1: Write GamePhase enum**

```python
# server/models/room.py (top portion)
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import uuid


class GamePhase(str, Enum):
    WAITING = "waiting"
    DRAWING = "drawing"
    ANSWERING = "answering"
    VOTING = "voting"
    REVEALING = "revealing"
    ROUND_END = "round_end"
    GAME_OVER = "game_over"
```

- [ ] **Step 2: Write Player model**

```python
# server/models/player.py
from dataclasses import dataclass, field
import uuid
import secrets


@dataclass
class Player:
    nickname: str
    room_id: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    token: str = field(default_factory=lambda: secrets.token_hex(16))
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
```

- [ ] **Step 3: Write Question model**

```python
# server/models/question.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Question:
    id: int
    term: str
    real_definition: str
    category: str = "通用"
    source: str = "builtin"
    contributor_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "term": self.term,
            "real_definition": self.real_definition,
            "category": self.category,
            "source": self.source,
        }
```

- [ ] **Step 4: Write Round and Game models**

```python
# server/models/room.py (continuation)
from server.models.player import Player
from server.models.question import Question


@dataclass
class Round:
    question: Question
    judge_id: str
    fake_answers: dict = field(default_factory=dict)       # player_id → text
    shuffled_answers: list = field(default_factory=list)    # [{text, is_real, player_id}]
    votes: dict = field(default_factory=dict)               # voter_id → answer_index
    scores_awarded: dict = field(default_factory=dict)      # player_id → int
    round_number: int = 0


@dataclass
class Game:
    rounds: list = field(default_factory=list)
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
    players: list = field(default_factory=list)
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
```

- [ ] **Step 5: Write model import**

```python
# server/models/__init__.py
from server.models.player import Player
from server.models.question import Question
from server.models.room import GamePhase, Room, Game, Round
```

- [ ] **Step 6: Write model tests**

```python
# server/tests/test_models.py
import pytest
from server.models import Player, Question, GamePhase, Room, Game, Round


class TestPlayer:
    def test_player_creation(self):
        p = Player(nickname="小明")
        assert p.nickname == "小明"
        assert len(p.id) == 12
        assert len(p.token) == 32
        assert p.score == 0
        assert p.is_connected is True

    def test_player_to_dict_excludes_token(self):
        p = Player(nickname="小明")
        d = p.to_dict()
        assert "token" not in d
        assert d["nickname"] == "小明"


class TestQuestion:
    def test_question_creation(self):
        q = Question(id=1, term="叶公好龙", real_definition="比喻口头上说爱好...")
        assert q.term == "叶公好龙"
        assert q.source == "builtin"


class TestGamePhase:
    def test_phases_exist(self):
        assert GamePhase.WAITING.value == "waiting"
        assert GamePhase.ANSWERING.value == "answering"


class TestRoom:
    def test_create_room(self):
        room = Room(id="AB12", host_id="host1")
        assert room.id == "AB12"
        assert room.phase == GamePhase.WAITING

    def test_add_player(self):
        room = Room(id="AB12")
        p = Player(nickname="小明")
        room.players.append(p)
        assert room.get_player(p.id) is not None

    def test_connected_players(self):
        room = Room(id="AB12")
        p1 = Player(nickname="A")
        p2 = Player(nickname="B")
        p2.is_connected = False
        room.players = [p1, p2]
        assert len(room.connected_players()) == 1
```

- [ ] **Step 7: Run tests**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/test_models.py -v
# Expected: 6 passed
```

- [ ] **Step 8: Commit**

```bash
git add server/models/ server/tests/test_models.py
git commit -m "feat: add Player, Question, Room, Game, Round models with tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Question bank + SQLite

**Files:**
- Create: `server/data/db.py`
- Create: `server/data/questions.json`
- Create: `server/tests/test_db.py`

- [ ] **Step 1: Write db.py**

```python
# server/data/db.py
import sqlite3
import json
import random
from pathlib import Path
from server.models.question import Question

DATA_DIR = Path(__file__).parent
DB_PATH = DATA_DIR / "dolos.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,
            real_definition TEXT NOT NULL,
            category TEXT DEFAULT '通用',
            source TEXT DEFAULT 'builtin',
            contributor_id TEXT
        )
    """)
    conn.commit()

    # Import built-in questions if table is empty
    count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    if count == 0:
        _import_builtin_questions(conn)

    conn.close()


def _import_builtin_questions(conn: sqlite3.Connection):
    json_path = DATA_DIR / "questions.json"
    if not json_path.exists():
        print(f"Warning: {json_path} not found, skipping import")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    for q in questions:
        conn.execute(
            "INSERT INTO questions (term, real_definition, category, source) VALUES (?, ?, ?, 'builtin')",
            (q["term"], q["definition"], q.get("category", "通用")),
        )
    conn.commit()
    print(f"Imported {len(questions)} built-in questions")


def get_random_question() -> Question | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    if row is None:
        return None
    return Question(
        id=row["id"],
        term=row["term"],
        real_definition=row["real_definition"],
        category=row["category"],
        source=row["source"],
        contributor_id=row["contributor_id"],
    )


def add_question(term: str, definition: str, category: str = "通用", contributor_id: str | None = None) -> Question:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO questions (term, real_definition, category, source, contributor_id) VALUES (?, ?, ?, 'player', ?)",
        (term, definition, category, contributor_id),
    )
    conn.commit()
    qid = cursor.lastrowid
    conn.close()
    return Question(id=qid, term=term, real_definition=definition, category=category, source="player", contributor_id=contributor_id)


def get_question_by_id(qid: int) -> Question | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    conn.close()
    if row is None:
        return None
    return Question(
        id=row["id"], term=row["term"], real_definition=row["real_definition"],
        category=row["category"], source=row["source"], contributor_id=row["contributor_id"],
    )


def get_question_count() -> int:
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    conn.close()
    return count
```

- [ ] **Step 2: Write sample questions.json**

```json
[
  {"term": "叶公好龙", "definition": "比喻口头上说爱好某事物，实际上并不真的爱好", "category": "成语"},
  {"term": "画蛇添足", "definition": "比喻做了多余的事，反而有害无益", "category": "成语"},
  {"term": "对牛弹琴", "definition": "比喻对不懂事理的人讲道理，白费口舌", "category": "成语"},
  {"term": "亡羊补牢", "definition": "比喻在受到损失之后想办法补救，免得以后再受损失", "category": "成语"},
  {"term": "掩耳盗铃", "definition": "比喻自己欺骗自己，明明掩盖不了的事情偏要设法掩盖", "category": "成语"},
  {"term": "杯弓蛇影", "definition": "比喻因疑神疑鬼而引起恐惧", "category": "成语"},
  {"term": "刻舟求剑", "definition": "比喻拘泥不变通，不懂得根据实际情况处理问题", "category": "成语"},
  {"term": "守株待兔", "definition": "比喻死守狭隘经验，不知变通", "category": "成语"},
  {"term": "买椟还珠", "definition": "比喻没有眼力，取舍不当", "category": "成语"},
  {"term": "邯郸学步", "definition": "比喻模仿别人不成，反而把自己原来的长处丢了", "category": "成语"},
  {"term": "量子纠缠", "definition": "两个粒子无论相隔多远，状态会瞬间相互关联的现象", "category": "科技术语"},
  {"term": "薛定谔的猫", "definition": "一个关于量子叠加态的思想实验，猫在盒子打开前同时处于生死两种状态", "category": "科技术语"},
  {"term": "彭罗斯阶梯", "definition": "一种不可能存在的几何结构，四条楼梯首尾相连却永远向上", "category": "冷知识"},
  {"term": "曼德拉效应", "definition": "指大众对历史的集体记忆与史实不符的现象", "category": "冷知识"},
  {"term": "忒修斯之船", "definition": "一个哲学悖论：如果一艘船的所有零件都被替换了，它还是原来那艘船吗", "category": "冷知识"}
]
```

- [ ] **Step 3: Write db tests**

```python
# server/tests/test_db.py
import pytest
from server.data.db import init_db, get_random_question, add_question, get_question_count


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


class TestQuestionBank:
    def test_init_db_populates_questions(self):
        count = get_question_count()
        assert count >= 10

    def test_get_random_question(self):
        q = get_random_question()
        assert q is not None
        assert q.term != ""
        assert q.real_definition != ""
        assert q.id > 0

    def test_add_question(self):
        q = add_question("测试词", "这是一个测试定义", "测试")
        assert q.term == "测试词"
        assert q.source == "player"

    def test_multiple_random_different(self):
        # Getting multiple random questions should (usually) not all be the same
        terms = set()
        for _ in range(5):
            q = get_random_question()
            if q:
                terms.add(q.term)
        # At least 2 different questions in 5 draws
        assert len(terms) >= 2
```

- [ ] **Step 4: Run tests**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/test_db.py -v
# Expected: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add server/data/
git commit -m "feat: add SQLite question bank with sample questions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: RoomManager

**Files:**
- Create: `server/managers/room_manager.py`
- Create: `server/tests/test_room_manager.py`

- [ ] **Step 1: Write RoomManager**

```python
# server/managers/room_manager.py
import random
import string
from server.models import Player, Room, GamePhase
from server.config import ROOM_CODE_CHARS, ROOM_CODE_LENGTH


class RoomManager:
    def __init__(self):
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
        if len(room.players) >= 8:
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


class RoomNotFoundError(Exception):
    pass


class RoomInGameError(Exception):
    pass


class RoomFullError(Exception):
    pass
```

- [ ] **Step 2: Write RoomManager tests**

```python
# server/tests/test_room_manager.py
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

    def test_remove_player_cleans_empty_room(self):
        rm = RoomManager()
        room, player = rm.create_room("唯一玩家")
        rm.remove_player(room.id, player.id)
        assert rm.get_room(room.id) is None

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
```

- [ ] **Step 3: Run tests**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/test_room_manager.py -v
# Expected: 8 passed
```

- [ ] **Step 4: Commit**

```bash
git add server/managers/room_manager.py server/tests/test_room_manager.py
git commit -m "feat: add RoomManager with create/join/remove/reconnect

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: GameEngine

**Files:**
- Create: `server/managers/game_engine.py`
- Create: `server/tests/test_game_engine.py`

- [ ] **Step 1: Write GameEngine**

```python
# server/managers/game_engine.py
import random
from server.models import Room, Game, Round, GamePhase, Player, Question
from server.config import MIN_PLAYERS


class GameError(Exception):
    pass


class InvalidPhaseError(GameError):
    pass


class NotHostError(GameError):
    pass


class NotJudgeError(GameError):
    pass


class NotEnoughPlayersError(GameError):
    pass


class GameEngine:
    def start_game(self, room: Room, host_id: str, question: Question) -> None:
        if room.phase != GamePhase.WAITING:
            raise InvalidPhaseError(f"当前阶段是 {room.phase.value}，无法开始")
        if host_id != room.host_id:
            raise NotHostError("只有房主可以开始游戏")
        if len(room.connected_players()) < MIN_PLAYERS:
            raise NotEnoughPlayersError(f"至少需要 {MIN_PLAYERS} 名玩家")

        # Reset all scores
        for p in room.players:
            p.score = 0

        game = Game(phase=GamePhase.DRAWING)
        room.current_game = game
        room.phase = GamePhase.DRAWING

    def judge_draw(self, room: Room, judge_id: str, question: Question) -> dict:
        self._validate_judge(room, judge_id)
        if room.phase != GamePhase.DRAWING:
            raise InvalidPhaseError("当前不是抽题阶段")

        game = room.current_game
        round_num = len(game.rounds)
        new_round = Round(
            question=question,
            judge_id=judge_id,
            round_number=round_num + 1,
        )
        game.rounds.append(new_round)
        game.current_round_index = len(game.rounds) - 1
        room.phase = GamePhase.ANSWERING

        return {
            "round_number": new_round.round_number,
            "judge_nickname": room.get_player(judge_id).nickname,
            "question_term": question.term,
        }

    def submit_answer(self, room: Room, player_id: str, text: str) -> None:
        if room.phase != GamePhase.ANSWERING:
            raise InvalidPhaseError("当前不在编答案阶段")
        if not text or not text.strip():
            raise GameError("答案不能为空")

        current_round = room.current_game.current_round
        if player_id == current_round.judge_id:
            raise GameError("法官不需要编答案")
        if player_id in current_round.fake_answers:
            raise GameError("你已经提交过了")

        current_round.fake_answers[player_id] = text.strip()

    def judge_collect(self, room: Room, judge_id: str) -> list[dict]:
        self._validate_judge(room, judge_id)
        if room.phase != GamePhase.ANSWERING:
            raise InvalidPhaseError("当前不在编答案阶段")

        current_round = room.current_game.current_round
        question = current_round.question

        # Build shuffled answer list
        answers = []
        # Real answer
        answers.append({
            "text": question.real_definition,
            "is_real": True,
            "player_id": "__REAL__",
        })
        # Fake answers
        for pid, text in current_round.fake_answers.items():
            answers.append({
                "text": text,
                "is_real": False,
                "player_id": pid,
            })

        random.shuffle(answers)
        current_round.shuffled_answers = answers

        room.phase = GamePhase.VOTING

        # Return vote options (without is_real and player_id)
        return [
            {"index": i, "text": a["text"]}
            for i, a in enumerate(answers)
        ]

    def cast_vote(self, room: Room, voter_id: str, answer_index: int) -> None:
        if room.phase != GamePhase.VOTING:
            raise InvalidPhaseError("当前不在投票阶段")
        current_round = room.current_game.current_round
        if voter_id == current_round.judge_id:
            raise GameError("法官不需要投票")
        if voter_id in current_round.votes:
            raise GameError("你已经投过票了")
        if answer_index < 0 or answer_index >= len(current_round.shuffled_answers):
            raise GameError("无效的选项")

        current_round.votes[voter_id] = answer_index

    def judge_end_vote(self, room: Room, judge_id: str) -> dict:
        self._validate_judge(room, judge_id)
        if room.phase != GamePhase.VOTING:
            raise InvalidPhaseError("当前不在投票阶段")

        current_round = room.current_game.current_round
        scores = self._calculate_scores(current_round, room.players)

        # Update player scores
        for pid, pts in scores.items():
            player = room.get_player(pid)
            if player:
                player.score += pts

        current_round.scores_awarded = scores

        # Find the correct answer index
        correct_index = None
        for i, a in enumerate(current_round.shuffled_answers):
            if a["is_real"]:
                correct_index = i
                break

        # Build per-player reveal data
        answer_details = []
        for i, a in enumerate(current_round.shuffled_answers):
            author = "系统（真答案）" if a["is_real"] else room.get_player(a["player_id"]).nickname
            answer_details.append({
                "index": i,
                "text": a["text"],
                "author": author,
                "is_real": a["is_real"],
                "vote_count": sum(1 for v in current_round.votes.values() if v == i),
            })

        # Build standings
        standings = sorted(room.players, key=lambda p: p.score, reverse=True)
        standings_data = [
            {"nickname": p.nickname, "score": p.score, "player_id": p.id}
            for p in standings
        ]

        room.phase = GamePhase.REVEALING

        return {
            "correct_index": correct_index,
            "answers": answer_details,
            "scores": {
                pid: {"pts": pts, "nickname": room.get_player(pid).nickname if room.get_player(pid) else "?"}
                for pid, pts in scores.items()
            },
            "standings": standings_data,
        }

    def next_round(self, room: Room, host_id: str) -> dict | None:
        if room.phase != GamePhase.REVEALING and room.phase != GamePhase.ROUND_END:
            raise InvalidPhaseError("当前不在回合结束阶段")
        if host_id != room.host_id:
            raise NotHostError("只有房主可以控制回合")

        game = room.current_game
        # Rotate judge
        connected = room.connected_players()
        if len(connected) < MIN_PLAYERS:
            raise NotEnoughPlayersError(f"人数不足 {MIN_PLAYERS}，无法继续")

        # Rotate judge to next connected player
        current_judge_idx = None
        for i, p in enumerate(connected):
            if p.id == game.current_round.judge_id:
                current_judge_idx = i
                break
        if current_judge_idx is not None:
            game.judge_index = (current_judge_idx + 1) % len(connected)

        next_judge = connected[game.judge_index]
        room.phase = GamePhase.DRAWING

        return {
            "next_judge_id": next_judge.id,
            "next_judge_nickname": next_judge.nickname,
            "round_number": len(game.rounds) + 1,
            "standings": [
                {"nickname": p.nickname, "score": p.score, "player_id": p.id}
                for p in sorted(room.players, key=lambda x: x.score, reverse=True)
            ],
        }

    def end_game(self, room: Room, host_id: str) -> dict:
        if host_id != room.host_id:
            raise NotHostError("只有房主可以结束游戏")
        room.phase = GamePhase.GAME_OVER
        standings = sorted(room.players, key=lambda p: p.score, reverse=True)
        return {
            "standings": [
                {"nickname": p.nickname, "score": p.score, "player_id": p.id}
                for p in standings
            ],
            "total_rounds": len(room.current_game.rounds) if room.current_game else 0,
        }

    def _validate_judge(self, room: Room, judge_id: str) -> None:
        if room.current_game is None or room.current_game.current_round is None:
            return  # DRAWING phase, no current round yet
        # In DRAWING phase, check that the player is the next judge
        if room.phase == GamePhase.DRAWING:
            connected = room.connected_players()
            if connected:
                expected_judge = connected[room.current_game.judge_index]
                if judge_id != expected_judge.id:
                    raise NotJudgeError(f"当前法官是 {expected_judge.nickname}")
        else:
            current_round = room.current_game.current_round
            if judge_id != current_round.judge_id:
                raise NotJudgeError("你不是本回合法官")

    def _calculate_scores(self, round_obj: Round, players: list[Player]) -> dict:
        from collections import defaultdict
        scores = defaultdict(int)
        correct_index = None
        for i, a in enumerate(round_obj.shuffled_answers):
            if a["is_real"]:
                correct_index = i
                break

        # +2 for correct guess
        for voter_id, voted_index in round_obj.votes.items():
            if voted_index == correct_index:
                scores[voter_id] += 2

        # +1 per fooled voter for each fake answer
        for i, a in enumerate(round_obj.shuffled_answers):
            if not a["is_real"]:
                fooled_count = sum(1 for v in round_obj.votes.values() if v == i)
                if fooled_count > 0:
                    scores[a["player_id"]] += fooled_count

        # Judge bonus: +3 if nobody guessed correctly
        correct_votes = sum(1 for v in round_obj.votes.values() if v == correct_index)
        if correct_votes == 0:
            scores[round_obj.judge_id] += 3

        return dict(scores)
```

- [ ] **Step 2: Write GameEngine tests**

```python
# server/tests/test_game_engine.py
import pytest
from server.managers.game_engine import (
    GameEngine, GameError, InvalidPhaseError, NotHostError,
    NotEnoughPlayersError, NotJudgeError,
)
from server.models import Room, Player, Question, GamePhase


def make_room_with_players(n=4):
    """Helper: create a room with n connected players"""
    room = Room(id="TEST")
    for i in range(n):
        p = Player(nickname=f"玩家{i+1}")
        room.players.append(p)
    room.host_id = room.players[0].id
    room.players[0].is_host = True
    return room


def make_question():
    return Question(id=1, term="测试题", real_definition="这是真定义")


class TestGameEngine:
    def setup_method(self):
        self.engine = GameEngine()

    def test_start_game_success(self):
        room = make_room_with_players(4)
        q = make_question()
        self.engine.start_game(room, room.host_id, q)
        assert room.phase == GamePhase.DRAWING
        assert room.current_game is not None

    def test_start_game_not_enough_players(self):
        room = make_room_with_players(3)
        with pytest.raises(NotEnoughPlayersError):
            self.engine.start_game(room, room.host_id, make_question())

    def test_start_game_not_host(self):
        room = make_room_with_players(4)
        non_host = room.players[1].id
        with pytest.raises(NotHostError):
            self.engine.start_game(room, non_host, make_question())

    def test_judge_draw_and_submit_answer(self):
        room = make_room_with_players(4)
        q = make_question()
        self.engine.start_game(room, room.host_id, q)

        # First judge is host (players[0])
        judge = room.players[0]
        result = self.engine.judge_draw(room, judge.id, q)
        assert room.phase == GamePhase.ANSWERING
        assert result["question_term"] == "测试题"

        # Non-judge players submit answers
        self.engine.submit_answer(room, room.players[1].id, "假定义1")
        self.engine.submit_answer(room, room.players[2].id, "假定义2")
        self.engine.submit_answer(room, room.players[3].id, "假定义3")

        current_round = room.current_game.current_round
        assert len(current_round.fake_answers) == 3

    def test_cannot_submit_twice(self):
        room = make_room_with_players(4)
        q = make_question()
        self.engine.start_game(room, room.host_id, q)
        self.engine.judge_draw(room, room.players[0].id, q)
        self.engine.submit_answer(room, room.players[1].id, "假定义1")
        with pytest.raises(GameError):
            self.engine.submit_answer(room, room.players[1].id, "假定义2")

    def test_judge_collect_creates_vote_options(self):
        room = make_room_with_players(4)
        q = make_question()
        self.engine.start_game(room, room.host_id, q)
        self.engine.judge_draw(room, room.players[0].id, q)
        self.engine.submit_answer(room, room.players[1].id, "假1")
        self.engine.submit_answer(room, room.players[2].id, "假2")
        self.engine.submit_answer(room, room.players[3].id, "假3")

        options = self.engine.judge_collect(room, room.players[0].id)
        assert room.phase == GamePhase.VOTING
        assert len(options) == 4  # 3 fake + 1 real

    def test_voting_and_reveal(self):
        room = make_room_with_players(4)
        q = make_question()
        self.engine.start_game(room, room.host_id, q)
        judge = room.players[0]
        self.engine.judge_draw(room, judge.id, q)
        self.engine.submit_answer(room, room.players[1].id, "假1")
        self.engine.submit_answer(room, room.players[2].id, "假2")
        self.engine.submit_answer(room, room.players[3].id, "假3")
        self.engine.judge_collect(room, judge.id)

        # Players 1,2,3 vote
        self.engine.cast_vote(room, room.players[1].id, 0)
        self.engine.cast_vote(room, room.players[2].id, 0)
        self.engine.cast_vote(room, room.players[3].id, 0)

        # End vote
        reveal = self.engine.judge_end_vote(room, judge.id)
        assert room.phase == GamePhase.REVEALING
        assert reveal["correct_index"] is not None
        assert len(reveal["answers"]) == 4
        assert len(reveal["standings"]) == 4

    def test_next_round_rotates_judge(self):
        room = make_room_with_players(4)
        q = make_question()
        self.engine.start_game(room, room.host_id, q)
        judge = room.players[0]
        self.engine.judge_draw(room, judge.id, q)
        self.engine.submit_answer(room, room.players[1].id, "假1")
        self.engine.submit_answer(room, room.players[2].id, "假2")
        self.engine.submit_answer(room, room.players[3].id, "假3")
        self.engine.judge_collect(room, judge.id)
        self.engine.cast_vote(room, room.players[1].id, 0)
        self.engine.cast_vote(room, room.players[2].id, 0)
        self.engine.cast_vote(room, room.players[3].id, 0)
        self.engine.judge_end_vote(room, judge.id)

        result = self.engine.next_round(room, room.host_id)
        assert room.phase == GamePhase.DRAWING
        # Next judge should be player 1 (index 1)
        assert result["next_judge_id"] == room.players[1].id

    def test_end_game(self):
        room = make_room_with_players(4)
        q = make_question()
        self.engine.start_game(room, room.host_id, q)
        self.engine.judge_draw(room, room.players[0].id, q)
        self.engine.submit_answer(room, room.players[1].id, "假1")
        self.engine.submit_answer(room, room.players[2].id, "假2")
        self.engine.submit_answer(room, room.players[3].id, "假3")
        self.engine.judge_collect(room, room.players[0].id)
        self.engine.cast_vote(room, room.players[1].id, 0)
        self.engine.cast_vote(room, room.players[2].id, 0)
        self.engine.cast_vote(room, room.players[3].id, 0)
        self.engine.judge_end_vote(room, room.players[0].id)

        result = self.engine.end_game(room, room.host_id)
        assert room.phase == GamePhase.GAME_OVER
        assert len(result["standings"]) == 4
```

- [ ] **Step 3: Run tests**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/test_game_engine.py -v
# Expected: 8 passed
```

- [ ] **Step 4: Commit**

```bash
git add server/managers/game_engine.py server/tests/test_game_engine.py
git commit -m "feat: add GameEngine with full state machine and scoring

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: WebSocket Manager

**Files:**
- Create: `server/managers/ws_manager.py`

- [ ] **Step 1: Write WSManager**

```python
# server/managers/ws_manager.py
from fastapi import WebSocket
import json


class WSManager:
    """Track WebSocket connections per room and broadcast messages."""

    def __init__(self):
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
```

- [ ] **Step 2: Commit**

```bash
git add server/managers/ws_manager.py
git commit -m "feat: add WSManager for WebSocket connection tracking and broadcast

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: HTTP routes + WebSocket handler

**Files:**
- Create: `server/routes/rooms.py`
- Create: `server/routes/ws.py`
- Create: `server/managers/__init__.py`
- Modify: `server/main.py`

- [ ] **Step 1: Write HTTP room routes**

```python
# server/routes/rooms.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.managers.room_manager import (
    RoomManager, RoomNotFoundError, RoomInGameError, RoomFullError,
)
from server.data.db import get_random_question

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


class CreateRoomRequest(BaseModel):
    nickname: str


class JoinRoomRequest(BaseModel):
    nickname: str


class CreateRoomResponse(BaseModel):
    room_id: str
    player_id: str
    token: str
    host_id: str


class JoinRoomResponse(BaseModel):
    room_id: str
    player_id: str
    token: str
    players: list[dict]


class RoomInfoResponse(BaseModel):
    id: str
    player_count: int
    phase: str
    exists: bool


def get_room_manager() -> RoomManager:
    from server.main import room_manager
    return room_manager


@router.post("", response_model=CreateRoomResponse)
async def create_room(req: CreateRoomRequest):
    rm = get_room_manager()
    if not req.nickname or not req.nickname.strip():
        raise HTTPException(status_code=400, detail="昵称不能为空")
    room, player = rm.create_room(req.nickname.strip())
    return CreateRoomResponse(
        room_id=room.id,
        player_id=player.id,
        token=player.token,
        host_id=room.host_id,
    )


@router.post("/{room_id}/join", response_model=JoinRoomResponse)
async def join_room(room_id: str, req: JoinRoomRequest):
    rm = get_room_manager()
    if not req.nickname or not req.nickname.strip():
        raise HTTPException(status_code=400, detail="昵称不能为空")
    try:
        room, player = rm.join_room(room_id, req.nickname.strip())
    except RoomNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RoomInGameError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RoomFullError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JoinRoomResponse(
        room_id=room.id,
        player_id=player.id,
        token=player.token,
        players=[p.to_dict() for p in room.players],
    )


@router.get("/{room_id}")
async def room_info(room_id: str):
    rm = get_room_manager()
    room = rm.get_room(room_id)
    if room is None:
        return RoomInfoResponse(id=room_id, player_count=0, phase="unknown", exists=False)
    return RoomInfoResponse(
        id=room.id,
        player_count=len(room.players),
        phase=room.phase.value,
        exists=True,
    )
```

- [ ] **Step 2: Write WebSocket handler**

```python
# server/routes/ws.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from server.managers.room_manager import RoomManager
from server.managers.game_engine import GameEngine, GameError
from server.managers.ws_manager import WSManager
from server.data.db import get_random_question
from server.models import GamePhase

router = APIRouter()


def get_managers():
    from server.main import room_manager, game_engine, ws_manager
    return room_manager, game_engine, ws_manager


@router.websocket("/ws/{room_id}")
async def game_websocket(
    ws: WebSocket,
    room_id: str,
    player_id: str = Query(...),
    token: str = Query(...),
):
    room_manager: RoomManager
    game_engine: GameEngine
    ws_manager: WSManager
    room_manager, game_engine, ws_manager = get_managers()

    # Authenticate: check if reconnecting or new
    room = room_manager.get_room(room_id)
    if room is None:
        await ws.accept()
        await ws.send_json({"type": "error", "message": "房间不存在"})
        await ws.close()
        return

    player = room.get_player(player_id)
    if player is None or player.token != token:
        await ws.accept()
        await ws.send_json({"type": "error", "message": "身份验证失败"})
        await ws.close()
        return

    # Connect
    await ws_manager.connect(room_id, player_id, ws)
    player.is_connected = True

    # Broadcast updated player list
    await ws_manager.broadcast_to_all(room_id, {
        "type": "room_update",
        "players": [p.to_dict() for p in room.players],
        "host_id": room.host_id,
        "phase": room.phase.value,
    })

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws_manager.send_to_player(room_id, player_id, {
                    "type": "error", "message": "无效的消息格式"
                })
                continue

            msg_type = msg.get("type", "")

            try:
                if msg_type == "start_game":
                    q = get_random_question()
                    if q is None:
                        await ws_manager.send_to_player(room_id, player_id, {
                            "type": "error", "message": "题库为空"
                        })
                        continue
                    game_engine.start_game(room, player_id, q)
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "phase_change",
                        "phase": room.phase.value,
                        "judge_id": room.players[0].id,
                    })

                elif msg_type == "judge_action":
                    action = msg.get("action", "")
                    if action == "draw":
                        q = get_random_question()
                        if q is None:
                            await ws_manager.send_to_player(room_id, player_id, {
                                "type": "error", "message": "题库为空"
                            })
                            continue
                        draw_info = game_engine.judge_draw(room, player_id, q)
                        # Send phase change with question to non-judge players
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                            "judge_id": player_id,
                            "question_term": q.term,
                            "round_number": draw_info["round_number"],
                        })
                        # Send full question info to judge
                        await ws_manager.send_to_player(room_id, player_id, {
                            "type": "judge_info",
                            "question_term": q.term,
                            "question_definition": q.real_definition,
                        })

                    elif action == "collect":
                        options = game_engine.judge_collect(room, player_id)
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "vote_options",
                            "options": options,
                        })
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                        })

                    elif action == "end_vote":
                        reveal = game_engine.judge_end_vote(room, player_id)
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "reveal",
                            **reveal,
                        })
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                        })

                elif msg_type == "submit_answer":
                    game_engine.submit_answer(room, player_id, msg["text"])
                    await ws_manager.send_to_player(room_id, player_id, {
                        "type": "answer_submitted",
                    })
                    # Notify judge of progress
                    current_round = room.current_game.current_round
                    await ws_manager.send_to_player(room_id, current_round.judge_id, {
                        "type": "answer_progress",
                        "received": len(current_round.fake_answers),
                        "total": len(room.connected_players()) - 1,
                    })

                elif msg_type == "cast_vote":
                    game_engine.cast_vote(room, player_id, msg["answer_index"])
                    await ws_manager.send_to_player(room_id, player_id, {
                        "type": "vote_cast",
                    })

                elif msg_type == "next_round":
                    info = game_engine.next_round(room, player_id)
                    if info:
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "round_start",
                            **info,
                        })
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                        })

                elif msg_type == "end_game":
                    result = game_engine.end_game(room, player_id)
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "game_over",
                        **result,
                    })

            except GameError as e:
                await ws_manager.send_to_player(room_id, player_id, {
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(room_id, player_id)
        room_manager.remove_player(room_id, player_id)
        # Broadcast updated player list to remaining players
        if room_manager.get_room(room_id):
            room = room_manager.get_room(room_id)
            await ws_manager.broadcast_to_all(room_id, {
                "type": "room_update",
                "players": [p.to_dict() for p in room.players],
                "host_id": room.host_id,
                "phase": room.phase.value,
            })
```

- [ ] **Step 3: Update main.py to wire everything**

```python
# server/main.py (replace content)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.managers.room_manager import RoomManager
from server.managers.game_engine import GameEngine
from server.managers.ws_manager import WSManager
from server.data.db import init_db
from server.routes import rooms, ws

# Initialize global singletons
room_manager = RoomManager()
game_engine = GameEngine()
ws_manager = WSManager()

app = FastAPI(title="Dolos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(ws.router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Write WebSocket integration test**

```python
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
```

- [ ] **Step 5: Run all backend tests**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/ -v
# Expected: all tests pass
```

- [ ] **Step 6: Commit**

```bash
git add server/routes/ server/main.py server/tests/test_ws.py
git commit -m "feat: add HTTP routes, WebSocket handler, and main.py wiring

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2 — Frontend Skeleton

### Task 8: Vite + Vue 3 project scaffold

**Files:**
- Create: `client/package.json`
- Create: `client/vite.config.js`
- Create: `client/index.html`
- Create: `client/src/main.js`
- Create: `client/src/App.vue`
- Create: `client/src/style.css`

- [ ] **Step 1: Initialize client project**

```bash
mkdir -p client/src/{views,components,stores,composables}
```

- [ ] **Step 2: Write package.json**

```json
{
  "name": "dolos-client",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.2.0"
  }
}
```

- [ ] **Step 3: Write vite.config.js**

```js
// client/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

- [ ] **Step 4: Write index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no" />
  <title>Dolos - 瞎掰王</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 5: Write main.js**

```js
// client/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 6: Write App.vue**

```html
<!-- client/src/App.vue -->
<template>
  <div class="app-container">
    <router-view />
  </div>
</template>

<script setup>
</script>
```

- [ ] **Step 7: Write global style.css**

```css
/* client/src/style.css */
:root {
  --bg: #0f0f23;
  --surface: #1a1a2e;
  --surface-hover: #16213e;
  --primary: #e94560;
  --accent: #4ecca3;
  --warn: #e9a800;
  --text: #eaeaea;
  --text-dim: #888888;
  --border: #333355;
  --radius: 12px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
}

#app {
  min-height: 100vh;
  max-width: 480px;
  margin: 0 auto;
  padding: 16px;
}

.app-container {
  min-height: 100vh;
}
```

- [ ] **Step 8: Install dependencies and verify**

```bash
cd client && npm install && npm run build
# Expected: build succeeds
```

- [ ] **Step 9: Commit**

```bash
git add client/
git commit -m "feat: scaffold Vue 3 + Vite + Pinia frontend

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Router + HomeView + stores

**Files:**
- Create: `client/src/router.js`
- Create: `client/src/stores/room.js`
- Create: `client/src/stores/game.js`
- Create: `client/src/composables/useWebSocket.js`
- Create: `client/src/views/HomeView.vue`
- Create: `client/src/views/RoomView.vue`
- Create: `client/src/views/GameView.vue`

- [ ] **Step 1: Write router**

```js
// client/src/router.js
import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import RoomView from './views/RoomView.vue'
import GameView from './views/GameView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/room/:id', name: 'room', component: RoomView },
  { path: '/room/:id/play', name: 'game', component: GameView },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
```

- [ ] **Step 2: Write room store**

```js
// client/src/stores/room.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useRoomStore = defineStore('room', () => {
  const roomId = ref('')
  const players = ref([])
  const myPlayerId = ref('')
  const myToken = ref('')
  const phase = ref('waiting')
  const hostId = ref('')
  const connected = ref(false)

  const isHost = computed(() => myPlayerId.value === hostId.value)
  const playerCount = computed(() => players.value.length)
  const canStart = computed(() => isHost.value && playerCount.value >= 4 && phase.value === 'waiting')

  function setRoom(data) {
    roomId.value = data.id
    players.value = data.players
    hostId.value = data.host_id
    phase.value = data.phase
  }

  function updateFromMessage(msg) {
    if (msg.type === 'room_update') {
      players.value = msg.players
      hostId.value = msg.host_id
      if (msg.phase) phase.value = msg.phase
    }
    if (msg.type === 'phase_change') {
      phase.value = msg.phase
    }
  }

  return {
    roomId, players, myPlayerId, myToken, phase, hostId, connected,
    isHost, playerCount, canStart,
    setRoom, updateFromMessage,
  }
})
```

- [ ] **Step 3: Write game store**

```js
// client/src/stores/game.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useGameStore = defineStore('game', () => {
  const questionTerm = ref('')
  const judgeId = ref('')
  const myAnswer = ref('')
  const answerSubmitted = ref(false)
  const voteOptions = ref([])       // [{index, text}]
  const myVote = ref(null)
  const voteCast = ref(false)
  const revealData = ref(null)      // {correct_index, answers[], scores, standings}
  const standings = ref([])         // [{nickname, score, player_id}]
  const gameOver = ref(false)

  const isJudge = computed(() => {
    const room = useRoomStore()
    return room.myPlayerId === judgeId.value
  })

  function setPhase(phase, data) {
    if (phase === 'answering') {
      questionTerm.value = data.question_term || ''
      judgeId.value = data.judge_id || ''
      myAnswer.value = ''
      answerSubmitted.value = false
      voteCast.value = false
      myVote.value = null
      voteOptions.value = []
      revealData.value = null
    }
    if (phase === 'voting') {
      // keep current state
    }
    if (phase === 'revealing') {
      // reveal data sent separately
    }
    if (phase === 'drawing') {
      answerSubmitted.value = false
      voteCast.value = false
      myVote.value = null
      voteOptions.value = []
      revealData.value = null
    }
  }

  function updateFromMessage(msg) {
    switch (msg.type) {
      case 'phase_change':
        setPhase(msg.phase, msg)
        break
      case 'judge_info':
        questionTerm.value = msg.question_term
        break
      case 'vote_options':
        voteOptions.value = msg.options
        break
      case 'reveal':
        revealData.value = msg
        if (msg.standings) standings.value = msg.standings
        break
      case 'answer_submitted':
        answerSubmitted.value = true
        break
      case 'vote_cast':
        voteCast.value = true
        break
      case 'game_over':
        gameOver.value = true
        if (msg.standings) standings.value = msg.standings
        break
      case 'round_start':
        if (msg.standings) standings.value = msg.standings
        judgeId.value = msg.next_judge_id
        break
    }
  }

  return {
    questionTerm, judgeId, myAnswer, answerSubmitted,
    voteOptions, myVote, voteCast, revealData, standings, gameOver,
    isJudge,
    setPhase, updateFromMessage,
  }
})
```

- [ ] **Step 4: Write useWebSocket composable**

```js
// client/src/composables/useWebSocket.js
import { ref } from 'vue'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'

export function useWebSocket() {
  const ws = ref(null)
  const roomStore = useRoomStore()
  const gameStore = useGameStore()

  function connect(roomId, playerId, token) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = location.host
    const url = `${protocol}//${host}/ws/${roomId}?player_id=${playerId}&token=${token}`

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      roomStore.connected = true
      console.log('WebSocket connected')
    }

    ws.value.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        roomStore.updateFromMessage(msg)
        gameStore.updateFromMessage(msg)

        // Navigate to game if phase changes from waiting
        if (msg.type === 'phase_change' && msg.phase !== 'waiting' && msg.phase !== 'game_over') {
          const currentPath = window.location.hash
          if (!currentPath.includes('/play')) {
            window.location.hash = `#/room/${roomId}/play`
          }
        }
      } catch (e) {
        console.error('WS message parse error:', e)
      }
    }

    ws.value.onclose = () => {
      roomStore.connected = false
      console.log('WebSocket disconnected')
    }

    ws.value.onerror = (err) => {
      console.error('WebSocket error:', err)
    }
  }

  function send(type, payload = {}) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, ...payload }))
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  return { connect, send, disconnect }
}
```

- [ ] **Step 5: Write HomeView**

```html
<!-- client/src/views/HomeView.vue -->
<template>
  <div class="home">
    <div class="logo">
      <h1>🎭 DOLOS</h1>
      <p class="subtitle">瞎掰王 — 看谁会忽悠</p>
    </div>

    <div class="card">
      <label class="label">你的昵称</label>
      <input
        v-model="nickname"
        class="input"
        placeholder="输入显示名称..."
        maxlength="12"
        @keyup.enter="createRoom"
      />

      <div class="actions">
        <button class="btn btn-primary" @click="createRoom" :disabled="!nickname.trim()">
          ✨ 创建新房间
        </button>

        <div class="divider">—— 或 ——</div>

        <div class="join-row">
          <input
            v-model="roomCode"
            class="input"
            placeholder="房间码"
            maxlength="4"
            @keyup.enter="joinRoom"
          />
          <button class="btn btn-secondary" @click="joinRoom" :disabled="!nickname.trim() || !roomCode.trim()">
            加入
          </button>
        </div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRoomStore } from '../stores/room'

const router = useRouter()
const roomStore = useRoomStore()

const nickname = ref('')
const roomCode = ref('')
const error = ref('')

async function createRoom() {
  if (!nickname.value.trim()) return
  error.value = ''
  try {
    const resp = await fetch('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nickname: nickname.value.trim() }),
    })
    if (!resp.ok) {
      const data = await resp.json()
      error.value = data.detail || '创建失败'
      return
    }
    const data = await resp.json()
    roomStore.roomId = data.room_id
    roomStore.myPlayerId = data.player_id
    roomStore.myToken = data.token
    roomStore.hostId = data.host_id
    router.push(`/room/${data.room_id}`)
  } catch (e) {
    error.value = '网络错误，请重试'
  }
}

async function joinRoom() {
  if (!nickname.value.trim() || !roomCode.value.trim()) return
  error.value = ''
  try {
    const resp = await fetch(`/api/rooms/${roomCode.value.trim().toUpperCase()}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nickname: nickname.value.trim() }),
    })
    if (!resp.ok) {
      const data = await resp.json()
      error.value = data.detail || '加入失败'
      return
    }
    const data = await resp.json()
    roomStore.roomId = data.room_id
    roomStore.myPlayerId = data.player_id
    roomStore.myToken = data.token
    roomStore.players = data.players
    router.push(`/room/${data.room_id}`)
  } catch (e) {
    error.value = '网络错误，请重试'
  }
}
</script>
```

- [ ] **Step 6: Write RoomView (lobby)**

```html
<!-- client/src/views/RoomView.vue -->
<template>
  <div class="lobby">
    <div class="room-header">
      <h2>🚪 房间大厅</h2>
      <div class="room-code">
        <span class="label">房间码</span>
        <span class="code">{{ roomStore.roomId }}</span>
      </div>
    </div>

    <div class="card">
      <h3>玩家 ({{ roomStore.playerCount }})</h3>
      <div class="player-list">
        <div
          v-for="p in roomStore.players"
          :key="p.id"
          class="player-item"
          :class="{ me: p.id === roomStore.myPlayerId, host: p.is_host }"
        >
          <span class="player-icon">{{ p.is_host ? '👑' : '🎭' }}</span>
          <span class="player-name">{{ p.nickname }}</span>
          <span v-if="p.id === roomStore.myPlayerId" class="tag">你</span>
          <span v-if="p.is_host" class="tag host-tag">房主</span>
        </div>
      </div>

      <button
        v-if="roomStore.isHost"
        class="btn btn-primary btn-lg"
        :disabled="!roomStore.canStart"
        @click="startGame"
      >
        {{ roomStore.canStart ? '🎮 开始游戏' : `等待玩家加入 (至少4人，当前${roomStore.playerCount}人)` }}
      </button>
      <p v-else class="waiting-hint">等待房主开始游戏...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useWebSocket } from '../composables/useWebSocket'

const route = useRoute()
const roomStore = useRoomStore()
const { connect, send } = useWebSocket()

onMounted(() => {
  const roomId = route.params.id
  connect(roomId, roomStore.myPlayerId, roomStore.myToken)
})

function startGame() {
  send('start_game')
}
</script>
```

- [ ] **Step 7: Write GameView placeholder**

```html
<!-- client/src/views/GameView.vue -->
<template>
  <div class="game">
    <p>Game is running... phase: {{ roomStore.phase }}</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'

const route = useRoute()
const roomStore = useRoomStore()
const gameStore = useGameStore()

onMounted(() => {
  if (!roomStore.connected) {
    const { connect } = useWebSocket()
    connect(route.params.id, roomStore.myPlayerId, roomStore.myToken)
  }
})
</script>
```

- [ ] **Step 8: Verify build**

```bash
cd client && npm run build
# Expected: build succeeds with all views
```

- [ ] **Step 9: Commit**

```bash
git add client/src/
git commit -m "feat: add router, stores, WebSocket composable, HomeView, RoomView, GameView placeholder

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 3 — Game Core Components

### Task 10: AnswerInput + VotingPanel + RevealPanel components

**Files:**
- Create: `client/src/components/AnswerInput.vue`
- Create: `client/src/components/VotingPanel.vue`
- Create: `client/src/components/RevealPanel.vue`
- Create: `client/src/components/ScoreBoard.vue`
- Create: `client/src/components/JudgePanel.vue`
- Create: `client/src/components/PlayerList.vue`
- Modify: `client/src/views/GameView.vue`

- [ ] **Step 1: Write AnswerInput**

```html
<!-- client/src/components/AnswerInput.vue -->
<template>
  <div class="answer-input">
    <div class="question-card">
      <div class="label">这道题是</div>
      <div class="term">{{ gameStore.questionTerm }}</div>
      <div class="hint">写出一个能骗过别人的假定义</div>
    </div>

    <div v-if="!gameStore.answerSubmitted">
      <textarea
        v-model="answer"
        class="textarea"
        placeholder="输入你的假定义..."
        maxlength="200"
      ></textarea>
      <button
        class="btn btn-primary btn-lg"
        :disabled="!answer.trim()"
        @click="submitAnswer"
      >
        提交答案
      </button>
    </div>

    <div v-else class="submitted-card">
      <p>✅ 已提交，等待其他玩家...</p>
      <p class="your-answer">「{{ gameStore.myAnswer }}」</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'

const gameStore = useGameStore()
const { send } = useWebSocket()
const answer = ref('')

function submitAnswer() {
  if (!answer.value.trim()) return
  gameStore.myAnswer = answer.value.trim()
  send('submit_answer', { text: gameStore.myAnswer })
}
</script>
```

- [ ] **Step 2: Write VotingPanel**

```html
<!-- client/src/components/VotingPanel.vue -->
<template>
  <div class="voting-panel">
    <div class="question-card">
      <div class="label">选出「{{ gameStore.questionTerm }}」的真定义</div>
    </div>

    <div class="vote-options">
      <div
        v-for="opt in gameStore.voteOptions"
        :key="opt.index"
        class="vote-option"
        :class="{ selected: selectedIndex === opt.index }"
        @click="selectOption(opt.index)"
      >
        <span class="letter">{{ letters[opt.index] }}</span>
        <span class="text">{{ opt.text }}</span>
      </div>
    </div>

    <button
      v-if="selectedIndex !== null && !gameStore.voteCast"
      class="btn btn-primary btn-lg"
      @click="castVote"
    >
      确认投票
    </button>

    <p v-if="gameStore.voteCast" class="voted-msg">✅ 已投票，等待揭晓...</p>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'

const gameStore = useGameStore()
const { send } = useWebSocket()
const selectedIndex = ref(null)
const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

function selectOption(index) {
  if (gameStore.voteCast) return
  selectedIndex.value = index
}

function castVote() {
  if (selectedIndex.value === null) return
  gameStore.myVote = selectedIndex.value
  send('cast_vote', { answer_index: selectedIndex.value })
}
</script>
```

- [ ] **Step 3: Write RevealPanel**

```html
<!-- client/src/components/RevealPanel.vue -->
<template>
  <div class="reveal-panel" v-if="gameStore.revealData">
    <div class="section-title">🏆 揭晓结果</div>

    <!-- Correct answer highlight -->
    <div class="correct-answer card">
      <div class="label">正确答案</div>
      <div class="text">{{ correctAnswer?.text }}</div>
      <div class="meta">{{ correctAnswer?.author }}</div>
    </div>

    <!-- All answers with vote counts -->
    <div class="card">
      <div
        v-for="a in gameStore.revealData.answers"
        :key="a.index"
        class="answer-row"
        :class="{ correct: a.is_real, voted: myVoteIndex === a.index }"
      >
        <span class="letter">{{ letters[a.index] }}</span>
        <div class="answer-content">
          <div class="answer-text">{{ a.text }}</div>
          <div class="answer-meta">
            {{ a.author }}
            <span v-if="myVoteIndex === a.index">← 你投了</span>
          </div>
        </div>
        <span class="vote-badge">{{ a.vote_count }}票</span>
      </div>
    </div>

    <!-- Round scores -->
    <div class="card" v-if="gameStore.revealData.scores && Object.keys(gameStore.revealData.scores).length">
      <div class="label">本回合得分</div>
      <div v-for="(s, pid) in gameStore.revealData.scores" :key="pid" class="score-row">
        ✅ {{ s.nickname }} +{{ s.pts }}分
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useGameStore } from '../stores/game'

const gameStore = useGameStore()
const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

const correctAnswer = computed(() => {
  if (!gameStore.revealData) return null
  return gameStore.revealData.answers.find(a => a.is_real) || null
})

const myVoteIndex = computed(() => gameStore.myVote)
</script>
```

- [ ] **Step 4: Write ScoreBoard**

```html
<!-- client/src/components/ScoreBoard.vue -->
<template>
  <div class="scoreboard" v-if="gameStore.standings.length">
    <div class="scoreboard-header" @click="expanded = !expanded">
      <span>🏅 排行榜</span>
      <span>{{ expanded ? '▲' : '▼' }}</span>
    </div>
    <div v-if="expanded" class="scoreboard-body">
      <div
        v-for="(p, i) in gameStore.standings"
        :key="p.player_id"
        class="standing-row"
        :class="{ me: p.player_id === roomStore.myPlayerId }"
      >
        <span class="rank">{{ medals[i] || i + 1 }}</span>
        <span class="name">{{ p.nickname }}</span>
        <span class="score">{{ p.score }}分</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGameStore } from '../stores/game'
import { useRoomStore } from '../stores/room'

const gameStore = useGameStore()
const roomStore = useRoomStore()
const expanded = ref(true)
const medals = ['🥇', '🥈', '🥉']
</script>
```

- [ ] **Step 5: Write JudgePanel**

```html
<!-- client/src/components/JudgePanel.vue -->
<template>
  <div class="judge-panel">
    <div class="judge-badge">👨‍⚖️ 你是法官</div>

    <!-- DRAWING phase -->
    <div v-if="roomStore.phase === 'drawing'">
      <button class="btn btn-primary btn-lg" @click="judgeAction('draw')">
        🃏 抽题
      </button>
    </div>

    <!-- ANSWERING phase -->
    <div v-if="roomStore.phase === 'answering'">
      <div class="judge-question-info card">
        <div class="label">题目</div>
        <div class="term">{{ gameStore.questionTerm }}</div>
        <div class="definition">{{ judgeDefinition }}</div>
      </div>
      <button class="btn btn-warn btn-lg" @click="judgeAction('collect')">
        📥 收答案 → 进入投票
      </button>
    </div>

    <!-- VOTING phase -->
    <div v-if="roomStore.phase === 'voting'">
      <p class="judge-hint">玩家正在投票...</p>
      <button class="btn btn-warn btn-lg" @click="judgeAction('end_vote')">
        🔔 结束投票 → 揭晓
      </button>
    </div>

    <!-- REVEALING phase -->
    <div v-if="roomStore.phase === 'revealing' || roomStore.phase === 'round_end'">
      <button
        v-if="roomStore.isHost"
        class="btn btn-primary btn-lg"
        @click="send('next_round')"
      >
        ▶ 下一回合
      </button>
      <button
        v-if="roomStore.isHost"
        class="btn btn-secondary"
        @click="send('end_game')"
      >
        🏁 结束游戏
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'

const roomStore = useRoomStore()
const gameStore = useGameStore()
const { send } = useWebSocket()
const judgeDefinition = ref('')

function judgeAction(action) {
  if (action === 'draw') {
    // Request a random question (server sends back via WS)
  }
  send('judge_action', { action })
}

// Listen for judge_info message
import { watch } from 'vue'
watch(() => gameStore.questionTerm, (val) => {
  // judge_info comes through gameStore updateFromMessage
})
</script>
```

- [ ] **Step 6: Write PlayerList**

```html
<!-- client/src/components/PlayerList.vue -->
<template>
  <div class="player-list-bar">
    <div
      v-for="p in roomStore.players"
      :key="p.id"
      class="player-dot"
      :class="{ judge: p.id === gameStore.judgeId, offline: !p.is_connected }"
    >
      <span class="dot-icon">{{ p.id === gameStore.judgeId ? '👨‍⚖️' : '🎭' }}</span>
      <span class="dot-name">{{ p.nickname }}</span>
      <span class="dot-score">{{ p.score }}</span>
    </div>
  </div>
</template>

<script setup>
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'

const roomStore = useRoomStore()
const gameStore = useGameStore()
</script>
```

- [ ] **Step 7: Update GameView with phase switching**

```html
<!-- client/src/views/GameView.vue (replace content) -->
<template>
  <div class="game">
    <!-- Persistent scoreboard -->
    <ScoreBoard />

    <!-- Phase-based content -->
    <div class="game-main">
      <!-- DRAWING: waiting for judge -->
      <div v-if="roomStore.phase === 'drawing'" class="phase-waiting">
        <p v-if="gameStore.isJudge">你是法官，请抽题</p>
        <p v-else>等待法官 {{ judgeNickname }} 抽题...</p>
      </div>

      <!-- ANSWERING: submit fake definition -->
      <AnswerInput v-if="roomStore.phase === 'answering' && !gameStore.isJudge" />
      <JudgePanel v-if="gameStore.isJudge && (roomStore.phase === 'drawing' || roomStore.phase === 'answering' || roomStore.phase === 'voting')" />

      <!-- VOTING: vote for real answer -->
      <VotingPanel v-if="roomStore.phase === 'voting' && !gameStore.isJudge" />

      <!-- REVEALING: show results -->
      <RevealPanel v-if="roomStore.phase === 'revealing' || roomStore.phase === 'round_end'" />

      <!-- GAME OVER -->
      <div v-if="roomStore.phase === 'game_over'" class="game-over">
        <h2>🏆 游戏结束!</h2>
        <div class="final-standings">
          <div
            v-for="(p, i) in gameStore.standings"
            :key="p.player_id"
            class="final-row"
          >
            <span class="rank">{{ ['🥇','🥈','🥉'][i] || `#${i+1}` }}</span>
            <span class="name">{{ p.nickname }}</span>
            <span class="score">{{ p.score }}分</span>
          </div>
        </div>
        <button class="btn btn-primary btn-lg" @click="$router.push('/')">
          返回首页
        </button>
      </div>
    </div>

    <!-- Judge panel at bottom for judge -->
    <JudgePanel v-if="gameStore.isJudge && roomStore.phase === 'revealing'" />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'
import ScoreBoard from '../components/ScoreBoard.vue'
import AnswerInput from '../components/AnswerInput.vue'
import VotingPanel from '../components/VotingPanel.vue'
import RevealPanel from '../components/RevealPanel.vue'
import JudgePanel from '../components/JudgePanel.vue'

const route = useRoute()
const roomStore = useRoomStore()
const gameStore = useGameStore()

const judgeNickname = computed(() => {
  const p = roomStore.players.find(p => p.id === gameStore.judgeId)
  return p ? p.nickname : '?'
})

onMounted(() => {
  if (!roomStore.connected) {
    const { connect } = useWebSocket()
    connect(route.params.id, roomStore.myPlayerId, roomStore.myToken)
  }
})
</script>
```

- [ ] **Step 8: Add component styles to style.css**

Append to `client/src/style.css`:

```css
/* --- Components --- */

/* Card */
.card {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 16px;
  margin-bottom: 16px;
}

.label {
  font-size: 12px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Input */
.input {
  width: 100%;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 16px;
  outline: none;
  transition: border-color 0.2s;
}
.input:focus {
  border-color: var(--primary);
}

.textarea {
  width: 100%;
  min-height: 100px;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 16px;
  resize: vertical;
  outline: none;
  font-family: inherit;
}
.textarea:focus {
  border-color: var(--primary);
}

/* Buttons */
.btn {
  display: block;
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  font-family: inherit;
}
.btn:active {
  transform: scale(0.98);
}
.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-primary {
  background: var(--primary);
  color: #fff;
}
.btn-secondary {
  background: var(--surface-hover);
  color: var(--text);
  border: 1px solid var(--border);
}
.btn-warn {
  background: var(--warn);
  color: #1a1a2e;
}
.btn-lg {
  margin-top: 16px;
}

/* Home */
.home {
  padding-top: 40px;
}
.logo {
  text-align: center;
  margin-bottom: 32px;
}
.logo h1 {
  font-size: 36px;
  color: var(--primary);
  letter-spacing: 6px;
}
.logo .subtitle {
  color: var(--text-dim);
  margin-top: 8px;
}
.actions {
  margin-top: 16px;
}
.divider {
  text-align: center;
  color: var(--text-dim);
  margin: 20px 0;
  font-size: 14px;
}
.join-row {
  display: flex;
  gap: 8px;
}
.join-row .input {
  flex: 1;
}
.join-row .btn {
  width: auto;
  white-space: nowrap;
  padding: 12px 20px;
}
.error {
  color: var(--primary);
  margin-top: 12px;
  text-align: center;
  font-size: 14px;
}

/* Lobby */
.room-header {
  margin-bottom: 20px;
}
.room-header h2 {
  margin-bottom: 8px;
}
.room-code {
  display: flex;
  gap: 12px;
  align-items: center;
}
.room-code .code {
  font-size: 28px;
  font-weight: bold;
  color: var(--primary);
  letter-spacing: 6px;
}
.player-list {
  margin: 12px 0;
}
.player-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 4px;
  font-size: 15px;
}
.player-item.me {
  background: var(--surface-hover);
}
.player-item .player-name {
  flex: 1;
}
.tag {
  font-size: 11px;
  background: var(--primary);
  color: #fff;
  padding: 2px 8px;
  border-radius: 10px;
}
.host-tag {
  background: var(--accent);
  color: #1a1a2e;
}
.waiting-hint {
  text-align: center;
  color: var(--text-dim);
  margin-top: 20px;
}

/* Game */
.game {
  padding-bottom: 100px;
}
.phase-waiting {
  text-align: center;
  padding: 40px 0;
  color: var(--text-dim);
  font-size: 18px;
}

/* Question card */
.question-card {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 20px;
  text-align: center;
  margin-bottom: 16px;
}
.question-card .term {
  font-size: 28px;
  font-weight: bold;
  color: var(--primary);
  margin: 8px 0;
}
.question-card .hint {
  font-size: 13px;
  color: var(--text-dim);
}

/* AnswerInput */
.submitted-card {
  text-align: center;
  padding: 24px;
  background: var(--surface);
  border-radius: var(--radius);
  border: 1px solid var(--accent);
}
.submitted-card .your-answer {
  color: var(--text-dim);
  margin-top: 8px;
  font-style: italic;
}

/* Voting */
.vote-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}
.vote-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  background: var(--surface);
  border-radius: 8px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.vote-option.selected {
  border-color: var(--accent);
  background: var(--surface-hover);
}
.vote-option .letter {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary);
  color: #fff;
  border-radius: 50%;
  font-weight: bold;
  font-size: 14px;
  flex-shrink: 0;
}
.voted-msg {
  text-align: center;
  color: var(--accent);
  font-size: 16px;
  padding: 20px;
}

/* Reveal */
.section-title {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 12px;
}
.correct-answer {
  border: 2px solid var(--accent);
}
.correct-answer .text {
  font-size: 18px;
  margin: 8px 0;
}
.correct-answer .meta {
  color: var(--text-dim);
  font-size: 13px;
}
.answer-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.answer-row:last-child {
  border-bottom: none;
}
.answer-row .letter {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-hover);
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
}
.answer-row.correct .letter {
  background: var(--accent);
  color: #1a1a2e;
}
.answer-row.voted .letter {
  background: var(--warn);
  color: #1a1a2e;
}
.answer-content {
  flex: 1;
}
.answer-meta {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 2px;
}
.vote-badge {
  background: var(--surface-hover);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  flex-shrink: 0;
}
.score-row {
  padding: 6px 0;
  font-size: 14px;
}

/* Scoreboard */
.scoreboard {
  position: sticky;
  top: 0;
  background: var(--surface);
  border-radius: 8px;
  margin-bottom: 16px;
  z-index: 10;
}
.scoreboard-header {
  display: flex;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  font-weight: bold;
  font-size: 14px;
}
.scoreboard-body {
  padding: 0 14px 10px;
}
.standing-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
}
.standing-row.me {
  color: var(--accent);
  font-weight: bold;
}
.standing-row .rank {
  width: 24px;
}
.standing-row .name {
  flex: 1;
}

/* JudgePanel */
.judge-panel {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  background: var(--surface);
  border-top: 2px solid var(--warn);
  padding: 16px;
  border-radius: 16px 16px 0 0;
  z-index: 20;
}
.judge-badge {
  text-align: center;
  font-size: 14px;
  color: var(--warn);
  margin-bottom: 8px;
}
.judge-question-info {
  background: var(--surface-hover);
  font-size: 14px;
}
.judge-question-info .term {
  font-size: 20px;
  color: var(--primary);
  font-weight: bold;
}
.judge-question-info .definition {
  color: var(--accent);
  margin-top: 4px;
  font-size: 14px;
}
.judge-hint {
  text-align: center;
  color: var(--text-dim);
  padding: 12px;
}
.judge-panel .btn {
  margin-top: 8px;
}

/* Game Over */
.game-over {
  text-align: center;
  padding-top: 20px;
}
.game-over h2 {
  font-size: 28px;
  margin-bottom: 20px;
}
.final-standings {
  margin-bottom: 24px;
}
.final-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--surface);
  border-radius: 8px;
  margin-bottom: 6px;
  font-size: 18px;
}
.final-row .rank {
  font-size: 24px;
}
.final-row .name {
  flex: 1;
}
.final-row .score {
  color: var(--accent);
  font-weight: bold;
}

/* PlayerList bar */
.player-list-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding: 8px;
  background: var(--surface);
  border-radius: 8px;
}
.player-dot {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 8px;
  background: var(--surface-hover);
  border-radius: 16px;
}
.player-dot.judge {
  border: 1px solid var(--warn);
}
.player-dot.offline {
  opacity: 0.4;
}
.dot-icon {
  font-size: 14px;
}
.dot-score {
  color: var(--accent);
  font-weight: bold;
}
```

- [ ] **Step 9: Verify build**

```bash
cd client && npm run build
# Expected: build succeeds
```

- [ ] **Step 10: Commit**

```bash
git add client/src/components/ client/src/views/GameView.vue client/src/style.css
git commit -m "feat: add AnswerInput, VotingPanel, RevealPanel, ScoreBoard, JudgePanel, PlayerList

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 4 — Polish

### Task 11: Fix JudgePanel to receive definition

**Files:**
- Modify: `client/src/stores/game.js`
- Modify: `client/src/components/JudgePanel.vue`

- [ ] **Step 1: Add judgeDefinition to game store**

Edit `client/src/stores/game.js` — in the `updateFromMessage` switch, add:

```js
case 'judge_info':
  questionTerm.value = msg.question_term
  // ADD this line:
  judgeDefinition.value = msg.question_definition
  break
```

And add these at the top of the store's state declarations:

```js
const judgeDefinition = ref('')
```

And add to the return statement:

```js
judgeDefinition,
```

- [ ] **Step 2: Update JudgePanel to use store value**

In `client/src/components/JudgePanel.vue`, remove the local `judgeDefinition` ref and use `gameStore.judgeDefinition`:

```html
<div class="definition">{{ gameStore.judgeDefinition }}</div>
```

Also remove the `ref` import for `judgeDefinition` (the local one) and the `watch` import/block — they're no longer needed.

- [ ] **Step 3: Verify build and commit**

```bash
cd client && npm run build
git add client/src/stores/game.js client/src/components/JudgePanel.vue
git commit -m "fix: judge panel uses game store for definition display

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: End-to-end manual test & fixes

- [ ] **Step 1: Start backend**

```bash
cd server && source .venv/bin/activate && uvicorn server.main:app --reload --port 8000 &
```

- [ ] **Step 2: Start frontend**

```bash
cd client && npm run dev &
```

- [ ] **Step 3: Manually test with multiple browser tabs**

```bash
# Open 4 browser tabs at http://localhost:5173
# Test flow:
# 1. Tab 1: create room as "小明"
# 2. Tabs 2-4: join with different nicknames
# 3. Host starts game
# 4. Judge draws a question
# 5. Non-judge players submit fake answers
# 6. Judge collects answers
# 7. All vote
# 8. Judge ends voting
# 9. Reveal results
# 10. Next round
```

- [ ] **Step 4: Fix any issues found during testing**

- [ ] **Step 5: Commit any fixes**

```bash
git add -A && git commit -m "fix: issues found during manual testing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: More built-in questions

**Files:**
- Modify: `server/data/questions.json`

- [ ] **Step 1: Expand questions.json to ~50 questions**

Add more questions to `server/data/questions.json` covering all categories. Delete the existing SQLite DB so it re-imports:

```bash
rm server/data/dolos.db
```

Restart the server to trigger re-import.

- [ ] **Step 2: Commit**

```bash
git add server/data/questions.json
git commit -m "data: expand built-in question bank

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Reconnect handling + final polish

**Files:**
- Modify: `client/src/composables/useWebSocket.js`
- Modify: `client/src/views/GameView.vue`

- [ ] **Step 1: Add auto-reconnect logic to useWebSocket**

```js
// In useWebSocket.js, add after ws.value.onclose:
let reconnectTimer = null

ws.value.onclose = () => {
  roomStore.connected = false
  console.log('WebSocket disconnected, attempting reconnect...')
  // Attempt reconnect after 2 seconds
  reconnectTimer = setTimeout(() => {
    connect(roomId, playerId, token)
  }, 2000)
}

// In disconnect(), clear timer:
function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
}
```

- [ ] **Step 2: Update .gitignore and add README**

Update `.gitignore` if needed. Write a brief `README.md` with how to run the project.

- [ ] **Step 3: Run all tests**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/ -v
cd client && npm run build
```

- [ ] **Step 4: Final commit**

```bash
git add -A && git commit -m "feat: add reconnect logic, README, and final polish

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Summary

**Total tasks:** 14
**Files created:** ~30
**Key deliverables:**
- FastAPI backend with room management, game engine, and WebSocket handler
- Vue 3 frontend with 3 views and 6 components
- SQLite question bank with sample data
- Full test suites for backend models, managers, and HTTP routes

**Phases:**
1. Backend skeleton (Tasks 1-7) — models, managers, HTTP/WS routes
2. Frontend skeleton (Tasks 8-9) — Vite scaffold, routing, stores
3. Game core components (Task 10) — all game UI components
4. Polish (Tasks 11-14) — bug fixes, expanded questions, reconnect
