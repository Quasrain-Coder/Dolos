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
