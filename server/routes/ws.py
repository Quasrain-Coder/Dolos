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
                        await ws_manager.broadcast_to_all(room_id, {
                            "type": "phase_change",
                            "phase": room.phase.value,
                            "judge_id": player_id,
                            "question_term": q.term,
                            "round_number": draw_info["round_number"],
                        })
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
        if room_manager.get_room(room_id):
            room = room_manager.get_room(room_id)
            await ws_manager.broadcast_to_all(room_id, {
                "type": "room_update",
                "players": [p.to_dict() for p in room.players],
                "host_id": room.host_id,
                "phase": room.phase.value,
            })
