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


class TestRound:
    def test_round_creation_with_defaults(self):
        q = Question(id=1, term="叶公好龙", real_definition="比喻口头上说爱好...")
        r = Round(question=q, judge_id="player1")
        assert r.judge_id == "player1"
        assert r.fake_answers == {}
        assert r.shuffled_answers == []
        assert r.votes == {}
        assert r.scores_awarded == {}
        assert r.round_number == 0

    def test_round_with_custom_values(self):
        q = Question(id=1, term="叶公好龙", real_definition="比喻")
        r = Round(question=q, judge_id="player1", round_number=2)
        r.fake_answers["p2"] = "假答案"
        assert r.fake_answers == {"p2": "假答案"}


class TestGame:
    def test_game_creation(self):
        g = Game()
        assert g.rounds == []
        assert g.current_round_index == -1
        assert g.judge_index == 0
        assert g.phase == GamePhase.WAITING

    def test_current_round_none_when_no_rounds(self):
        g = Game()
        assert g.current_round is None

    def test_current_round_returns_correct_round(self):
        g = Game()
        q = Question(id=1, term="叶公好龙", real_definition="比喻")
        r = Round(question=q, judge_id="p1", round_number=1)
        g.rounds.append(r)
        g.current_round_index = 0
        assert g.current_round is r
        assert g.current_round.round_number == 1

    def test_current_round_none_when_index_out_of_range(self):
        g = Game()
        q = Question(id=1, term="叶公好龙", real_definition="比喻")
        g.rounds.append(Round(question=q, judge_id="p1"))
        g.current_round_index = 5  # out of range
        assert g.current_round is None


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
