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
