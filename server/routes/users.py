# server/routes/users.py
from fastapi import APIRouter, Depends
from server.auth import get_current_user

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
