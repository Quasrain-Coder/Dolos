# server/routes/auth.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from server.auth import authenticate, register_user, get_current_user, delete_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


@router.post("/register", response_model=AuthResponse)
async def register(req: AuthRequest):
    if not req.username or not req.username.strip():
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if len(req.username.strip()) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")
    if len(req.username.strip()) > 20:
        raise HTTPException(status_code=400, detail="用户名最多20个字符")
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")

    user = register_user(req.username.strip(), req.password)
    if user is None:
        raise HTTPException(status_code=409, detail="用户名已存在")
    return AuthResponse(
        token=user["token"],
        user={
            "id": user["id"],
            "username": user["username"],
            "total_games": user["total_games"],
            "total_wins": user["total_wins"],
            "total_score": user["total_score"],
            "created_at": user["created_at"],
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: AuthRequest):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = authenticate(req.username.strip(), req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名不存在或密码错误")
    return AuthResponse(
        token=user["token"],
        user={
            "id": user["id"],
            "username": user["username"],
            "total_games": user["total_games"],
            "total_wins": user["total_wins"],
            "total_score": user["total_score"],
            "created_at": user["created_at"],
        },
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user), authorization: str = Header(None)):
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if token:
        delete_session(token)
    return {"ok": True}
