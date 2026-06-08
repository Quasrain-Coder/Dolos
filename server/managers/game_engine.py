import random
from collections import defaultdict
from server.models import Room, Game, Round, GamePhase, GameMode, Player, Question
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
    def get_candidates(self, room: Room, count: int = 3) -> list[dict]:
        """Get candidate questions for detective selection. Draws from DB."""
        from server.data.db import get_random_questions
        questions = get_random_questions(count)
        room.current_game.candidate_questions = [{"term": q.term, "definition": q.real_definition, "category": q.category, "id": q.id} for q in questions]
        return [{"term": q.term, "category": q.category} for q in questions]

    def refresh_candidates(self, room: Room, count: int = 3) -> list[dict]:
        """Replace candidate questions with fresh ones."""
        from server.data.db import get_random_questions
        questions = get_random_questions(count)
        room.current_game.candidate_questions = [{"term": q.term, "definition": q.real_definition, "category": q.category, "id": q.id} for q in questions]
        return [{"term": q.term, "category": q.category} for q in questions]

    def select_question(self, room: Room, player_id: str, index: int) -> dict:
        """Detective selects a question from candidates. Uses pre-assigned roles."""
        game = room.current_game
        if game is None or game.mode != GameMode.WHO_IS_HONEST:
            raise GameError("当前不是「谁是老实人」模式")
        if room.phase != GamePhase.SELECTING:
            raise GameError("当前不是选题阶段")
        candidates = game.candidate_questions
        if not candidates or index < 0 or index >= len(candidates):
            raise GameError("无效的选项")
        selected = candidates[index]
        q = Question(id=selected["id"], term=selected["term"], real_definition=selected["definition"], category=selected.get("category", "通用"))
        # Use pre-assigned roles from SELECTING phase
        roles = getattr(game, 'mode2_roles', {})
        round_info = self.mode2_start_round(room, q, roles=roles)
        return round_info

    def start_game(self, room: Room, host_id: str, question: Question, mode: str = "classic") -> None:
        if room.phase != GamePhase.WAITING:
            raise InvalidPhaseError(f"当前阶段是 {room.phase.value}，无法开始")
        if host_id != room.host_id:
            raise NotHostError("只有房主可以开始游戏")
        if len(room.connected_players()) < MIN_PLAYERS:
            raise NotEnoughPlayersError(f"至少需要 {MIN_PLAYERS} 名玩家")

        # Reset all scores
        for p in room.players:
            p.score = 0

        game_mode = GameMode(mode)
        game = Game(phase=GamePhase.DRAWING, mode=game_mode)
        room.current_game = game
        room.phase = GamePhase.DRAWING

    def _assign_roles(self, room: Room) -> dict[str, str]:
        """Mode 2: randomly assign honest, detective, bluffer roles. Returns {player_id: role}."""
        players = room.connected_players()
        if len(players) < 2:
            raise NotEnoughPlayersError("至少需要 2 名玩家")

        # Randomly pick honest and detective
        selected = random.sample(players, 2)
        roles = {}
        for p in players:
            if p.id == selected[0].id:
                roles[p.id] = "honest"
            elif p.id == selected[1].id:
                roles[p.id] = "detective"
            else:
                roles[p.id] = "bluffer"
        return roles

    def mode2_start_round(self, room: Room, question: Question, roles: dict | None = None) -> dict:
        """Mode 2: auto-start a round. Uses provided roles or assigns new ones."""
        if room.current_game is None or room.current_game.mode != GameMode.WHO_IS_HONEST:
            raise InvalidPhaseError("当前不是「谁是老实人」模式")
        if room.phase not in (GamePhase.DRAWING, GamePhase.SELECTING):
            raise InvalidPhaseError("当前不是抽题或选题阶段")

        game = room.current_game
        if roles is None:
            roles = self._assign_roles(room)

        honest_id = None
        detective_id = None
        for pid, role in roles.items():
            if role == "honest":
                honest_id = pid
            elif role == "detective":
                detective_id = pid

        round_num = len(game.rounds)
        new_round = Round(
            question=question,
            judge_id="",  # no judge in mode 2
            round_number=round_num + 1,
            honest_player_id=honest_id or "",
            detective_player_id=detective_id or "",
        )
        game.rounds.append(new_round)
        game.current_round_index = len(game.rounds) - 1
        room.phase = GamePhase.ANSWERING

        return {
            "round_number": new_round.round_number,
            "question_term": question.term,
            "roles": roles,  # {player_id: role}
            "question_definition": question.real_definition,  # for honest player
        }

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
        game = room.current_game

        # Mode 1 (classic): judge doesn't submit
        if game.mode == GameMode.CLASSIC:
            if player_id == current_round.judge_id:
                raise GameError("法官不需要编答案")

        # Mode 2: honest + bluffers submit; detective doesn't (detective only guesses)
        if game.mode == GameMode.WHO_IS_HONEST:
            if player_id == current_round.detective_player_id:
                raise GameError("大聪明不需要编答案，你只需要猜谁是老实人")

        if player_id in current_round.fake_answers:
            raise GameError("你已经提交过了")

        current_round.fake_answers[player_id] = text.strip()

    def judge_collect(self, room: Room, judge_id: str) -> list[dict]:
        """Mode 1: judge collects answers. Mode 2: system collects (no judge)."""
        game = room.current_game

        if game.mode == GameMode.CLASSIC:
            self._validate_judge(room, judge_id)

        if room.phase != GamePhase.ANSWERING:
            raise InvalidPhaseError("当前不在编答案阶段")

        return self._collect_answers(room)

    def _collect_answers(self, room: Room) -> list[dict]:
        """Internal: build shuffled answer list and transition to voting."""
        current_round = room.current_game.current_round
        question = current_round.question
        game = room.current_game

        answers = []

        if game.mode == GameMode.CLASSIC:
            # Real answer from system
            answers.append({
                "text": question.real_definition,
                "is_real": True,
                "player_id": "__REAL__",
            })
        elif game.mode == GameMode.WHO_IS_HONEST:
            # Real answer is the honest player's submission
            honest_id = current_round.honest_player_id
            if honest_id in current_round.fake_answers:
                answers.append({
                    "text": current_round.fake_answers[honest_id],
                    "is_real": True,
                    "player_id": honest_id,
                })
            # Remove honest from fake_answers so it's not duplicated
            fake_for_shuffle = {
                pid: text for pid, text in current_round.fake_answers.items()
                if pid != honest_id
            }
        else:
            fake_for_shuffle = dict(current_round.fake_answers)

        if game.mode != GameMode.WHO_IS_HONEST:
            fake_for_shuffle = dict(current_round.fake_answers)

        # Add fake answers
        for pid, text in fake_for_shuffle.items():
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

    def cast_vote(self, room: Room, voter_id: str, answer_index: int) -> dict | None:
        """Record a vote. In mode 2, detective can re-vote after wrong guesses.
        Returns result dict on mode 2 correct guess, None otherwise."""
        if room.phase != GamePhase.VOTING:
            raise InvalidPhaseError("当前不在投票阶段")
        current_round = room.current_game.current_round
        game = room.current_game

        # Mode 1: judge doesn't vote; no re-voting
        if game.mode == GameMode.CLASSIC:
            if voter_id == current_round.judge_id:
                raise GameError("法官不需要投票")
            if voter_id in current_round.votes:
                raise GameError("你已经投过票了")

        # Mode 2: only detective votes; can re-vote
        if game.mode == GameMode.WHO_IS_HONEST:
            if voter_id != current_round.detective_player_id:
                raise GameError("只有大聪明可以投票")
            if answer_index in current_round.detective_wrong_answer_indices:
                raise GameError("你已经选过这个了")
            if answer_index < 0 or answer_index >= len(current_round.shuffled_answers):
                raise GameError("无效的选项")

            # Check if this is the correct answer
            correct_index = None
            for i, a in enumerate(current_round.shuffled_answers):
                if a["is_real"]:
                    correct_index = i
                    break

            is_correct = (answer_index == correct_index)

            if is_correct:
                # Correct! Reveal round and continue to ready-for-next.
                current_round.votes[voter_id] = answer_index
                # Award +2 for correct guess
                detective = room.get_player(voter_id)
                if detective:
                    detective.score += 2
                # Calculate fooled points (detective was fooled by these wrong answers)
                for wrong_idx in current_round.detective_wrong_answer_indices:
                    fooled_player_id = current_round.shuffled_answers[wrong_idx]["player_id"]
                    fooled_player = room.get_player(fooled_player_id)
                    if fooled_player and fooled_player_id != "__REAL__":
                        fooled_player.score += 1

                room.phase = GamePhase.REVEALING
                standings = sorted(room.players, key=lambda p: p.score, reverse=True)
                return {
                    "is_correct": True,
                    "correct_index": correct_index,
                    "question_term": current_round.question.term,
                    "question_definition": current_round.question.real_definition,
                    "honest_player_id": current_round.honest_player_id,
                    "honest_nickname": room.get_player(current_round.honest_player_id).nickname if room.get_player(current_round.honest_player_id) else "?",
                    "wrong_count": len(current_round.detective_wrong_answer_indices),
                    "standings": [
                        {"nickname": p.nickname, "score": p.score, "player_id": p.id}
                        for p in standings
                    ],
                }
            else:
                # Wrong — record and let detective try again
                current_round.detective_wrong_answer_indices.append(answer_index)
                current_round.votes[voter_id] = answer_index  # track latest vote
                return {
                    "is_correct": False,
                    "wrong_index": answer_index,
                }
        else:
            # Mode 1: normal vote
            if answer_index < 0 or answer_index >= len(current_round.shuffled_answers):
                raise GameError("无效的选项")
            current_round.votes[voter_id] = answer_index

        return None

    def judge_end_vote(self, room: Room, judge_id: str) -> dict:
        game = room.current_game

        if game.mode == GameMode.CLASSIC:
            self._validate_judge(room, judge_id)

        if room.phase != GamePhase.VOTING:
            raise InvalidPhaseError("当前不在投票阶段")

        return self._end_vote(room)

    def _end_vote(self, room: Room) -> dict:
        """Internal: calculate scores, build reveal data, transition to revealing."""
        current_round = room.current_game.current_round
        game = room.current_game
        scores = self._calculate_scores(current_round, room.players, game.mode)

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

        # Build answer details
        answer_details = []
        for i, a in enumerate(current_round.shuffled_answers):
            if game.mode == GameMode.CLASSIC:
                author = "系统（真答案）" if a["is_real"] else room.get_player(a["player_id"]).nickname
            else:
                # Mode 2: real answer has a player author
                author = room.get_player(a["player_id"]).nickname if room.get_player(a["player_id"]) else "?"
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

    def submit_detective_guess(self, room: Room, player_id: str, guessed_player_id: str) -> dict:
        """Mode 2: detective guesses who the honest player is.
        Can guess multiple times until correct. On correct guess, game ends."""
        game = room.current_game
        if game is None or game.mode != GameMode.WHO_IS_HONEST:
            raise GameError("当前不是「谁是老实人」模式")
        current_round = game.current_round
        if current_round is None:
            raise GameError("当前没有进行中的回合")
        if player_id != current_round.detective_player_id:
            raise GameError("只有大聪明可以进行猜测")
        if guessed_player_id == player_id:
            raise GameError("不能猜自己")
        if guessed_player_id in current_round.detective_wrong_guesses:
            raise GameError("你已经猜过这个玩家了，请猜别人")

        is_correct = guessed_player_id == current_round.honest_player_id

        if is_correct:
            current_round.detective_guess = guessed_player_id
            # Award +3 to detective
            detective = room.get_player(player_id)
            if detective:
                detective.score += 3
            if player_id in current_round.scores_awarded:
                current_round.scores_awarded[player_id] += 3
            else:
                current_round.scores_awarded[player_id] = 3
            # End the game
            room.phase = GamePhase.GAME_OVER

            # Build final standings
            standings = sorted(room.players, key=lambda p: p.score, reverse=True)
            return {
                "is_correct": True,
                "guessed_player_id": guessed_player_id,
                "honest_player_id": current_round.honest_player_id,
                "honest_nickname": room.get_player(current_round.honest_player_id).nickname if room.get_player(current_round.honest_player_id) else "?",
                "question_term": current_round.question.term,
                "question_definition": current_round.question.real_definition,
                "game_over": True,
                "standings": [
                    {"nickname": p.nickname, "score": p.score, "player_id": p.id}
                    for p in standings
                ],
            }
        else:
            # Wrong guess — track it, let detective try again
            current_round.detective_wrong_guesses.append(guessed_player_id)
            wrong_nickname = room.get_player(guessed_player_id).nickname if room.get_player(guessed_player_id) else "?"
            return {
                "is_correct": False,
                "guessed_player_id": guessed_player_id,
                "wrong_nickname": wrong_nickname,
                "wrong_guesses": list(current_round.detective_wrong_guesses),
                "game_over": False,
            }

    def player_ready_for_next(self, room: Room, player_id: str) -> dict:
        """Called when a player clicks 'ready for next round'. Returns progress.
        When all connected players are ready, triggers next_round internally."""
        if room.phase != GamePhase.REVEALING and room.phase != GamePhase.ROUND_END:
            raise InvalidPhaseError("当前不是揭露或回合结束阶段")

        game = room.current_game
        if player_id in game.ready_for_next:
            raise GameError("你已经就绪了")

        game.ready_for_next.add(player_id)
        connected = room.connected_players()
        total = len(connected)
        ready_count = len([pid for pid in game.ready_for_next if any(p.id == pid for p in connected)])
        all_ready = ready_count >= total

        progress = {
            "ready_count": ready_count,
            "total_count": total,
            "ready_player_ids": [pid for pid in game.ready_for_next if any(p.id == pid for p in connected)],
            "all_ready": all_ready,
        }

        if all_ready:
            # Trigger actual next round
            round_info = self._do_next_round(room)
            progress["round_info"] = round_info

        return progress

    def _do_next_round(self, room: Room) -> dict | None:
        """Internal: perform the actual round transition and return info."""
        game = room.current_game
        connected = room.connected_players()

        if len(connected) < MIN_PLAYERS:
            raise NotEnoughPlayersError(f"人数不足 {MIN_PLAYERS}，无法继续")

        # Clear ready set for next round
        game.ready_for_next.clear()

        if game.mode == GameMode.CLASSIC:
            # Rotate judge to next connected player
            current_judge_idx = None
            for i, p in enumerate(connected):
                if p.id == game.current_round.judge_id:
                    current_judge_idx = i
                    break
            if current_judge_idx is not None:
                game.judge_index = (current_judge_idx + 1) % len(connected)
            next_judge = connected[game.judge_index]
            game.next_judge_id = next_judge.id
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
        else:
            # Mode 2: no judge rotation, just go back to DRAWING
            room.phase = GamePhase.DRAWING
            return {
                "round_number": len(game.rounds) + 1,
                "standings": [
                    {"nickname": p.nickname, "score": p.score, "player_id": p.id}
                    for p in sorted(room.players, key=lambda x: x.score, reverse=True)
                ],
            }

    def next_round(self, room: Room, host_id: str) -> dict | None:
        """Legacy method — kept for backward compatibility. Use player_ready_for_next instead."""
        if host_id != room.host_id:
            raise NotHostError("只有房主可以控制回合")
        return self._do_next_round(room)

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
        if room.phase == GamePhase.DRAWING:
            game = room.current_game
            if game is None:
                return
            if game.next_judge_id:
                if judge_id != game.next_judge_id:
                    raise NotJudgeError("你不是本回合的法官")
            else:
                # First round: host is judge (judge_index = 0)
                connected = room.connected_players()
                if connected:
                    expected_judge = connected[game.judge_index]
                    if judge_id != expected_judge.id:
                        raise NotJudgeError(f"当前法官是 {expected_judge.nickname}")
        elif room.current_game is not None and room.current_game.current_round is not None:
            current_round = room.current_game.current_round
            if judge_id != current_round.judge_id:
                raise NotJudgeError("你不是本回合法官")

    def _calculate_scores(self, round_obj: Round, players: list[Player], mode: GameMode = GameMode.CLASSIC) -> dict:
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

        if mode == GameMode.CLASSIC:
            # Judge bonus: +3 if nobody guessed correctly
            correct_votes = sum(1 for v in round_obj.votes.values() if v == correct_index)
            if correct_votes == 0:
                scores[round_obj.judge_id] += 3
        # Mode 2: no judge bonus; detective bonus is handled in submit_detective_guess

        return dict(scores)
