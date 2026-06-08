# server/auth.py
import secrets
from fastapi import Header, HTTPException
from passlib.context import CryptContext
from server.data.db import get_user_by_token, get_user_by_username, create_user, create_session, delete_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def generate_token() -> str:
    return secrets.token_hex(16)


def authenticate(username: str, password: str) -> dict | None:
    """Validate credentials and return user dict with a fresh token."""
    user = get_user_by_username(username)
    if user is None:
        return None
    if not verify_password(password, user["password"]):
        return None
    token = generate_token()
    create_session(user["id"], token)
    user["token"] = token
    return user


def register_user(username: str, password: str) -> dict | None:
    """Create a new user account. Returns None if username taken."""
    hashed = hash_password(password)
    token = generate_token()
    user = create_user(username, hashed)
    if user is None:
        return None
    create_session(user["id"], token)
    user["token"] = token
    return user


def get_current_user(authorization: str = Header(None)) -> dict:
    """FastAPI dependency: extract user from Authorization: Bearer <token>."""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="认证格式错误")
    token = authorization[7:]
    user = get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="无效的认证信息")
    return user
