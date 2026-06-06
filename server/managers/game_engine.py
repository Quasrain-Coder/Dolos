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
