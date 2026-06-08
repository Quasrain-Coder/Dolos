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

        # Send role info to reconnecting player
        if cr:
            if player_id == cr.honest_player_id:
                sync["my_role"] = "honest"
                sync["question_definition"] = cr.question.real_definition
            elif player_id == cr.detective_player_id:
                sync["my_role"] = "detective"
            else:
                sync["my_role"] = "bluffer"
            sync["question_term"] = cr.question.term
            sync["question_category"] = cr.question.category

        if cr:
            # Send vote options if in voting or later
            if room.phase.value in ("voting", "revealing", "round_end") and cr.shuffled_answers:
                if player_id == cr.detective_player_id:
                    sync["vote_options"] = [
                        {"index": i, "text": a["text"], "author": room.get_player(a["player_id"]).nickname if room.get_player(a["player_id"]) else "?"}
                        for i, a in enumerate(cr.shuffled_answers)
                    ]
                else:
                    sync["waiting_for_detective_vote"] = True
            # If already submitted
            if player_id in cr.fake_answers:
                sync["answer_submitted"] = True
            # If already voted
            if player_id in cr.votes:
                sync["vote_cast"] = True
            # Mode 2: sync wrong answer indices for detective
            if game.mode == GameMode.WHO_IS_HONEST and player_id == cr.detective_player_id:
                sync["detective_wrong_indices"] = list(cr.detective_wrong_answer_indices)

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

                    # Enter SELECTING phase — detective picks from 3 candidates
                    room.phase = GamePhase.SELECTING
                    roles = game_engine._assign_roles(room)
                    game.mode2_roles = roles
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "phase_change",
                        "phase": room.phase.value,
                    })
                    for pid, role in roles.items():
                        role_msg = {"type": "role_info", "role": role}
                        await ws_manager.send_to_player(room_id, pid, role_msg)
                    detective_id = next((pid for pid, r in roles.items() if r == "detective"), None)
                    if detective_id:
                        candidates = game_engine.get_candidates(room)
                        await ws_manager.send_to_player(room_id, detective_id, {
                            "type": "candidate_questions",
                            "questions": candidates,
                        })

                elif msg_type == "refresh_candidates":
                    candidates = game_engine.refresh_candidates(room)
                    await ws_manager.send_to_player(room_id, player_id, {
                        "type": "candidate_questions",
                        "questions": candidates,
                    })

                elif msg_type == "select_question":
                    index = msg.get("index", 0)
                    round_info = game_engine.select_question(room, player_id, index)
                    # Broadcast selected question and phase change to all
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "phase_change",
                        "phase": room.phase.value,
                        "question_term": round_info["question_term"],
                        "question_category": room.current_game.current_round.question.category if room.current_game and room.current_game.current_round else "",
                        "round_number": round_info["round_number"],
                    })
                    # Send role info (honest gets definition)
                    for pid, role in round_info["roles"].items():
                        role_msg = {"type": "role_info", "role": role}
                        if role == "honest":
                            role_msg["question_definition"] = round_info["question_definition"]
                        await ws_manager.send_to_player(room_id, pid, role_msg)

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

                    # All except detective submit; auto-collect when done
                    total_expected = len(room.connected_players()) - 1  # exclude detective
                    if len(current_round.fake_answers) >= total_expected:
                        options = game_engine.judge_collect(room, "")
                        for opt in options:
                            answer = current_round.shuffled_answers[opt["index"]]
                            player = room.get_player(answer["player_id"])
                            opt["author"] = player.nickname if player else "?"
                        await ws_manager.send_to_player(room_id, current_round.detective_player_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                        })
                        await ws_manager.send_to_player(room_id, current_round.detective_player_id, {
                            "type": "vote_options",
                            "options": options,
                        })
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
                        if game:
                            room.phase = GamePhase.SELECTING
                            roles = game_engine._assign_roles(room)
                            game.mode2_roles = roles
                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "round_start",
                                "round_number": info.get("round_number", 0),
                                "standings": info.get("standings", []),
                            })
                            await ws_manager.broadcast_to_all(room_id, {
                                "type": "phase_change",
                                "phase": room.phase.value,
                            })
                            for pid, role in roles.items():
                                role_msg = {"type": "role_info", "role": role}
                                await ws_manager.send_to_player(room_id, pid, role_msg)
                            detective_id = next((pid for pid, r in roles.items() if r == "detective"), None)
                            if detective_id:
                                candidates = game_engine.get_candidates(room)
                                await ws_manager.send_to_player(room_id, detective_id, {
                                    "type": "candidate_questions",
                                    "questions": candidates,
                                })

                elif msg_type == "end_game":
                    result = game_engine.end_game(room, player_id)
                    await ws_manager.broadcast_to_all(room_id, {
                        "type": "game_over",
                        "mode": "who_is_honest",
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


