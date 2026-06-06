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
