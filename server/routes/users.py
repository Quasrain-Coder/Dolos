# server/routes/users.py
from fastapi import APIRouter, Depends, HTTPException
from server.auth import get_current_user
from server.data.db import get_user_by_id

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "total_games": current_user["total_games"],
        "total_wins": current_user["total_wins"],
        "total_score": current_user["total_score"],
        "created_at": current_user["created_at"],
    }


@router.get("/{user_id}")
async def get_user_stats(user_id: int):
    """Public endpoint: get any registered user's stats by user_id."""
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "id": user["id"],
        "username": user["username"],
        "total_games": user["total_games"],
        "total_wins": user["total_wins"],
        "total_score": user["total_score"],
        "created_at": user["created_at"],
    }
