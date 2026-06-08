# server/main.py
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.managers.room_manager import RoomManager
from server.managers.game_engine import GameEngine
from server.managers.ws_manager import WSManager
from server.data.db import init_db
from server.routes import rooms, ws, auth, users

# Initialize global singletons
room_manager = RoomManager()
game_engine = GameEngine()
ws_manager = WSManager()

app = FastAPI(title="Dolos")

# CORS — allow all in dev, restrict in prod via env
allow_origins = os.getenv("ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API + WebSocket routes
app.include_router(rooms.router)
app.include_router(ws.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve built frontend (for production)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "client" / "dist"

if FRONTEND_DIR.exists():
    # Mount static assets (js, css, images, etc.)
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA fallback: serve index.html for any non-API route
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
