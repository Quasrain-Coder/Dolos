# server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.managers.room_manager import RoomManager
from server.managers.game_engine import GameEngine
from server.managers.ws_manager import WSManager
from server.data.db import init_db
from server.routes import rooms, ws

# Initialize global singletons
room_manager = RoomManager()
game_engine = GameEngine()
ws_manager = WSManager()

app = FastAPI(title="Dolos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(ws.router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}
