# server/routes/ws.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from server.managers.room_manager import RoomManager
from server.managers.game_engine import GameEngine, GameError
from server.managers.ws_manager import WSManager
from server.data.db import get_random_question, update_user_stats
from server.models import GamePhase, GameMode

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

    # Authenticate
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
        "mode": room.mode.value,
    })

    # If game is in progress, sync current state to reconnected player
    if room.phase.value not in ("waiting", "game_over") and room.current_game:
        game = room.current_game
        cr = game.current_round
        sync = {
            "type": "state_sync",
            "phase": room.phase.value,
            "mode": game.mode.value,
        }

        if game.mode == GameMode.CLASSIC:
            sync["judge_id"] = cr.judge_id if cr else room.players[0].id
        else:
            # Mode 2: send role info to reconnecting player
            if cr:
                if player_id == cr.honest_player_id:
                    sync["my_role"] = "honest"
                    sync["question_definition"] = cr.question.real_definition
                elif player_id == cr.detective_player_id:
                    sync["my_role"] = "detective"
                else:
                    sync["my_role"] = "bluffer"
                sync["question_term"] = cr.question.term

        if cr:
            if not sync.get("question_term"):
                sync["question_term"] = cr.question.term
            if cr:
                sync["question_category"] = cr.question.category
            # Send vote options if in voting or later
            # Mode 2: only detective gets vote_options; others get waiting flag
            if room.phase.value in ("voting", "revealing", "round_end") and cr.shuffled_answers:
                if game.mode == GameMode.WHO_IS_HONEST:
                    if player_id == cr.detective_player_id:
                        sync["vote_options"] = [
                            {"index": i, "text": a["text"], "author": room.get_player(a["player_id"]).nickname if room.get_player(a["player_id"]) else "?"}
                            for i, a in enumerate(cr.shuffled_answers)
                        ]
                    else:
                        sync["waiting_for_detective_vote"] = True
                else:
                    sync["vote_options"] = [
                        {"index": i, "text": a["text"]}
                        for i, a in enumerate(cr.shuffled_answers)
                    ]
            # If already submitted
            if player_id in cr.fake_answers:
                sync["answer_submitted"] = True
            # If already voted
            if player_id in cr.votes:
                sync["vote_cast"] = True
            # Mode 2: sync wrong answer indices for detective
            if game.mode == GameMode.WHO_IS_HONEST and player_id == cr.detective_player_id:
                sync["detective_wrong_indices"] = list(cr.detective_wrong_answer_indices)

        # Re-send reveal data if in reveal phase (classic mode only)
        if room.phase.value in ("revealing", "round_end") and cr and game.mode == GameMode.CLASSIC:
            correct_index = None
            for i, a in enumerate(cr.shuffled_answers):
                if a["is_real"]:
                    correct_index = i
                    break
            answer_details = []
            for i, a in enumerate(cr.shuffled_answers):
                author = "系统（真答案）" if a["is_real"] else (room.get_player(a["player_id"]).nickname if room.get_player(a["player_id"]) else "?")
                answer_details.append({
                    "index": i,
                    "text": a["text"],
                    "author": author,
                    "is_real": a["is_real"],
                    "vote_count": sum(1 for v in cr.votes.values() if v == i),
                })
            sync["reveal_data"] = {
                "correct_index": correct_index,
                "answers": answer_details,
                "standings": [
                    {"nickname": p.nickname, "score": p.score, "player_id": p.id}
                    for p in sorted(room.players, key=lambda x: x.score, reverse=True)
                ],
            }

        # Sync ready progress if in reveal/round_end phase
        if room.phase.value in ("revealing", "round_end") and game:
            connected = room.connected_players()
            ready_ids = [pid for pid in game.ready_for_next if any(p.id == pid for p in connected)]
            sync["ready_progress"] = {
                "ready_count": len(ready_ids),
                "total_count": len(connected),
                "ready_player_ids": ready_ids,
                "all_ready": len(ready_ids) >= len(connected),
            }

        await ws_manager.send_to_player(room_id, player_id, sync)

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

                    mode = msg.get("mode", room.mode.value)
                    game_engine.start_game(room, player_id, q, mode)
                    game = room.current_game
                    room.phase = GamePhase.DRAWING

                    if game and game.mode == GameMode.WHO_IS_HONEST:
                        # Mode 2: auto-start first round
                        q2 = get_random_question()
                        if q2 is None:
                            await ws_manager.send_to_player(room_id, player_id, {
                                "type": "error", "message": "题库为空"
                            })
                            continue
                        round_info = game_engine.mode2_start_round(room, q2)
                        # Send phase change to all
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                            "question_term": q2.term,
                            "question_category": q2.category,
                            "round_number": round_info["round_number"],
                        })
                        # Send role info privately to each player
                        for pid, role in round_info["roles"].items():
                            role_msg = {
                                "type": "role_info",
                                "role": role,
                            }
                            if role == "honest":
                                role_msg["question_definition"] = round_info["question_definition"]
                            await ws_manager.send_to_player(room_id, pid, role_msg)
                    else:
                        # Mode 1 (classic): existing behavior
                        room.phase = GamePhase.DRAWING
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
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                            "judge_id": player_id,
                            "question_term": q.term,
                            "question_category": q.category,
                            "round_number": draw_info["round_number"],
                        })
                        await ws_manager.send_to_player(room_id, player_id, {
                            "type": "judge_info",
                            "question_term": q.term,
                            "question_category": q.category,
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
                        await _broadcast_reveal(room, room_manager, game_engine, ws_manager, room_id, reveal)
                    else:
                        await ws_manager.send_to_player(room_id, player_id, {
                            "type": "error", "message": f"未知操作: {action}"
                        })

                elif msg_type == "submit_answer":
                    text = msg.get("text")
                    if text is None:
                        await ws_manager.send_to_player(room_id, player_id, {
                            "type": "error", "message": "缺少 text 字段"
                        })
                        continue
                    game_engine.submit_answer(room, player_id, text)
                    await ws_manager.send_to_player(room_id, player_id, {
                        "type": "answer_submitted",
                    })
                    # Broadcast who submitted to all players
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "player_status",
                        "submitted_players": list(room.current_game.current_round.fake_answers.keys()),
                        "voted_players": list(room.current_game.current_round.votes.keys()),
                    })

                    game = room.current_game
                    current_round = game.current_round

                    if game.mode == GameMode.CLASSIC:
                        # Mode 1: notify judge of progress
                        total_expected = len(room.connected_players()) - 1  # exclude judge
                        await ws_manager.send_to_player(room_id, current_round.judge_id, {
                            "type": "answer_progress",
                            "received": len(current_round.fake_answers),
                            "total": total_expected,
                        })
                        # Auto-collect when all non-judge players have submitted
                        if len(current_round.fake_answers) >= total_expected:
                            options = game_engine.judge_collect(room, current_round.judge_id)
                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "vote_options",
                                "options": options,
                            })
                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "phase_change",
                                "phase": room.phase.value,
                            })
                    else:
                        # Mode 2: all except detective submit (detective only guesses)
                        total_expected = len(room.connected_players()) - 1  # exclude detective
                        if len(current_round.fake_answers) >= total_expected:
                            options = game_engine.judge_collect(room, "")
                            # Add author names for detective's vote options
                            for opt in options:
                                answer = current_round.shuffled_answers[opt["index"]]
                                player = room.get_player(answer["player_id"])
                                opt["author"] = player.nickname if player else "?"
                            # Send vote options + phase_change to detective
                            await ws_manager.send_to_player(room_id, current_round.detective_player_id, {
                                "type": "phase_change",
                                "phase": room.phase.value,
                            })
                            await ws_manager.send_to_player(room_id, current_round.detective_player_id, {
                                "type": "vote_options",
                                "options": options,
                            })
                            # Tell others detective is voting
                            for p in room.connected_players():
                                if p.id != current_round.detective_player_id:
                                    await ws_manager.send_to_player(room_id, p.id, {
                                        "type": "phase_change",
                                        "phase": room.phase.value,
                                        "waiting_for_detective_vote": True,
                                    })

                elif msg_type == "cast_vote":
                    answer_index = msg.get("answer_index")
                    if answer_index is None:
                        await ws_manager.send_to_player(room_id, player_id, {
                            "type": "error", "message": "缺少 answer_index 字段"
                        })
                        continue
                    result = game_engine.cast_vote(room, player_id, answer_index)
                    game = room.current_game
                    current_round = game.current_round

                    if game.mode == GameMode.WHO_IS_HONEST:
                        # Mode 2: detective's vote IS their guess
                        if result is None:
                            # Shouldn't happen in mode 2
                            await ws_manager.send_to_player(room_id, player_id, {
                                "type": "vote_cast",
                            })
                        elif result["is_correct"]:
                            # Correct! Game over. Build full reveal + broadcast.
                            full_answers = []
                            for i, a in enumerate(current_round.shuffled_answers):
                                author = room.get_player(a["player_id"]).nickname if room.get_player(a["player_id"]) else "?"
                                full_answers.append({
                                    "index": i,
                                    "text": a["text"],
                                    "author": author,
                                    "is_real": a["is_real"],
                                    "vote_count": 1 if i == answer_index else 0,
                                })

                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "detective_correct",
                                "correct_index": result["correct_index"],
                                "honest_nickname": result["honest_nickname"],
                                "question_term": result["question_term"],
                                "question_category": current_round.question.category,
                                "question_definition": result["question_definition"],
                                "wrong_count": result["wrong_count"],
                                "answers": full_answers,
                                "standings": result["standings"],
                            })

                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "phase_change",
                                "phase": "revealing",
                            })

                            # Send ready progress
                            game.ready_for_next.clear()
                            connected = room.connected_players()
                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "ready_progress",
                                "ready_count": 0,
                                "total_count": len(connected),
                                "ready_player_ids": [],
                                "all_ready": False,
                            })
                            # Update user stats for registered players
                            for entry in result["standings"]:
                                pid = entry["player_id"]
                                player = room.get_player(pid)
                                if player and player.user_id is not None:
                                    is_winner = (entry == result["standings"][0])
                                    update_user_stats(player.user_id, entry["score"], is_winner)
                        else:
                            # Wrong vote — tell detective to try again
                            await ws_manager.send_to_player(room_id, player_id, {
                                "type": "vote_wrong",
                                "wrong_index": result["wrong_index"],
                                "message": "这不是真定义，再选！",
                            })
                            # Tell others detective is still trying
                            for p in room.connected_players():
                                if p.id != player_id:
                                    await ws_manager.send_to_player(room_id, p.id, {
                                        "type": "detective_retry",
                                        "wrong_count": len(current_round.detective_wrong_answer_indices),
                                    })
                    else:
                        # Mode 1: normal voting
                        await ws_manager.send_to_player(room_id, player_id, {
                            "type": "vote_cast",
                        })
                        # Broadcast who voted to all
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "player_status",
                            "submitted_players": list(current_round.fake_answers.keys()),
                            "voted_players": list(current_round.votes.keys()),
                        })
                        total_voters = len(room.connected_players()) - 1  # exclude judge
                        if len(current_round.votes) >= total_voters:
                            reveal = game_engine.judge_end_vote(room, current_round.judge_id)
                            await _broadcast_reveal(room, room_manager, game_engine, ws_manager, room_id, reveal)

                elif msg_type == "ready_next_round":
                    progress = game_engine.player_ready_for_next(room, player_id)
                    # Broadcast progress to all
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "ready_progress",
                        "ready_count": progress["ready_count"],
                        "total_count": progress["total_count"],
                        "ready_player_ids": progress["ready_player_ids"],
                        "all_ready": progress["all_ready"],
                    })
                    # If all ready, trigger next round transition
                    if progress["all_ready"] and progress.get("round_info"):
                        info = progress["round_info"]
                        game = room.current_game
                        if game and game.mode == GameMode.WHO_IS_HONEST:
                            # Mode 2: auto-start next round with new roles
                            q = get_random_question()
                            if q is None:
                                await ws_manager.send_to_player(room_id, player_id, {
                                    "type": "error", "message": "题库为空"
                                })
                                continue
                            round_info = game_engine.mode2_start_round(room, q)
                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "round_start",
                                "round_number": round_info["round_number"],
                                "standings": info.get("standings", []),
                            })
                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "phase_change",
                                "phase": room.phase.value,
                                "question_term": q.term,
                                "question_category": q.category,
                                "round_number": round_info["round_number"],
                            })
                            # Send role info privately
                            for pid, role in round_info["roles"].items():
                                role_msg = {
                                    "type": "role_info",
                                    "role": role,
                                }
                                if role == "honest":
                                    role_msg["question_definition"] = round_info["question_definition"]
                                await ws_manager.send_to_player(room_id, pid, role_msg)
                        else:
                            # Mode 1: judge rotates
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
                        "mode": room.current_game.mode.value if room.current_game else "classic",
                        **result,
                    })
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "phase_change",
                        "phase": "game_over",
                    })
                    # Update user stats for registered players
                    standings = result.get("standings", [])
                    if standings:
                        winner_id = standings[0]["player_id"]
                        for entry in standings:
                            pid = entry["player_id"]
                            player = room.get_player(pid)
                            if player and player.user_id is not None:
                                is_winner = (pid == winner_id)
                                update_user_stats(player.user_id, entry["score"], is_winner)

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
        if room_manager.get_room(room_id):
            room = room_manager.get_room(room_id)
            # If the host disconnected, pass host to the first connected player
            if room.host_id == player_id:
                # Clear old host flag
                old_host = room.get_player(player_id)
                if old_host:
                    old_host.is_host = False
                connected = room.connected_players()
                if connected:
                    room.host_id = connected[0].id
                    connected[0].is_host = True
            await ws_manager.broadcast_to_all(room_id, {
                "type": "room_update",
                "players": [p.to_dict() for p in room.players],
                "host_id": room.host_id,
                "phase": room.phase.value,
                "mode": room.mode.value,
            })


async def _broadcast_reveal(room, room_manager, game_engine, ws_manager, room_id, reveal_data):
    """Broadcast reveal results for classic mode."""
    game = room.current_game

    await ws_manager.broadcast_to_all(room_id, {
        "type": "reveal",
        **reveal_data,
    })
    await ws_manager.broadcast_to_all(room_id, {
        "type": "phase_change",
        "phase": room.phase.value,
    })

    # Clear ready set for new reveal phase, broadcast initial ready progress
    game.ready_for_next.clear()
    connected = room.connected_players()
    await ws_manager.broadcast_to_all(room_id, {
        "type": "ready_progress",
        "ready_count": 0,
        "total_count": len(connected),
        "ready_player_ids": [],
        "all_ready": False,
    })
