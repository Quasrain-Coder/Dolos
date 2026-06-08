# User Registration & Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional user registration/login with bcrypt-hashed passwords, token-based auth, and persistent player profiles with game statistics.

**Architecture:** New `users` table in SQLite, new auth routes (`/api/auth/*`) and user route (`/api/users/me`), `Player` model extended with optional `user_id`. Password hashing via passlib+bcrypt. Auth token is `secrets.token_hex(16)` — same format as anonymous player tokens. Frontend adds LoginModal, ProfilePanel, and auth state in the room store.

**Tech Stack:** Python (passlib[bcrypt], secrets), Vue 3 (Pinia, Composition API), SQLite

**Source spec:** `docs/superpowers/specs/2026-06-08-user-registration-design.md`

---

### Task 1: Add passlib dependency and users table

**Files:**
- Modify: `server/requirements.txt`
- Modify: `server/data/db.py`

- [ ] **Step 1: Add passlib to requirements**

Edit `server/requirements.txt`, add `passlib[bcrypt]`:

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.7.0
passlib[bcrypt]>=1.7.4
httpx>=0.27.0
```

- [ ] **Step 2: Install the new dependency**

```bash
cd server && source .venv/bin/activate && pip install passlib[bcrypt]
```

- [ ] **Step 3: Add users table to init_db and user CRUD functions**

Edit `server/data/db.py`, add the users table to `init_db()` and append new functions:

In `init_db()`, after the `questions` table creation, add:

```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            token TEXT,
            total_games INTEGER DEFAULT 0,
            total_wins INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
```

Append these functions at the end of the file:

```python
def create_user(username: str, password_hash: str, token: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password, token) VALUES (?, ?, ?)",
            (username, password_hash, token),
        )
        conn.commit()
        uid = cursor.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_user_by_token(token: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def update_user_token(user_id: int, token: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE users SET token = ? WHERE id = ?", (token, user_id))
    conn.commit()
    conn.close()


def clear_user_token(user_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE users SET token = NULL WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_user_stats(user_id: int, score: int, is_winner: bool) -> None:
    conn = get_connection()
    if is_winner:
        conn.execute(
            "UPDATE users SET total_games = total_games + 1, total_score = total_score + ?, total_wins = total_wins + 1 WHERE id = ?",
            (score, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET total_games = total_games + 1, total_score = total_score + ? WHERE id = ?",
            (score, user_id),
        )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Verify the table was created and functions work**

```bash
cd server && source .venv/bin/activate && python -c "
from server.data.db import init_db, create_user, get_user_by_username
init_db()
r = create_user('testuser', 'fakehash', 'testtoken')
print('created:', r)
u = get_user_by_username('testuser')
print('found:', u)
"
```
Expected: prints the created and found user dicts.

- [ ] **Step 5: Commit**

```bash
git add server/requirements.txt server/data/db.py
git commit -m "feat: add passlib dependency and users table with CRUD functions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Create auth dependency helper

**Files:**
- Create: `server/auth.py`

- [ ] **Step 1: Create auth helper module**

Create `server/auth.py`:

```python
# server/auth.py
import secrets
from fastapi import Header, HTTPException
from passlib.context import CryptContext
from server.data.db import get_user_by_token, get_user_by_username, create_user, update_user_token, clear_user_token

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
    update_user_token(user["id"], token)
    user["token"] = token
    return user


def register_user(username: str, password: str) -> dict | None:
    """Create a new user account. Returns None if username taken."""
    hashed = hash_password(password)
    token = generate_token()
    user = create_user(username, hashed, token)
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
```

- [ ] **Step 2: Verify auth functions work**

```bash
cd server && source .venv/bin/activate && python -c "
from server.auth import hash_password, verify_password, generate_token
h = hash_password('mypassword')
assert verify_password('mypassword', h)
assert not verify_password('wrong', h)
t = generate_token()
assert len(t) == 32
print('auth functions OK')
"
```
Expected: `auth functions OK`

- [ ] **Step 3: Commit**

```bash
git add server/auth.py
git commit -m "feat: add auth helper module with bcrypt hashing and token management

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Create auth routes (register, login, logout)

**Files:**
- Create: `server/routes/auth.py`

- [ ] **Step 1: Create auth routes file**

Create `server/routes/auth.py`:

```python
# server/routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from server.auth import authenticate, register_user, get_current_user, clear_user_token

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
async def logout(current_user: dict = Depends(get_current_user)):
    clear_user_token(current_user["id"])
    return {"ok": True}
```

- [ ] **Step 2: Register auth routes in main.py**

Edit `server/main.py`. Add the import after existing route imports:

```python
from server.routes import rooms, ws, auth
```

Add the router registration after `app.include_router(ws.router)`:

```python
app.include_router(auth.router)
```

- [ ] **Step 3: Test register endpoint manually**

Start the server:
```bash
cd server && source .venv/bin/activate && uvicorn server.main:app --port 8000 &
```

Test register:
```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}' | python -m json.tool
```
Expected: `{"token": "<hex>", "user": {"id": 1, "username": "alice", ...}}`

- [ ] **Step 4: Test login and duplicate register**

Test duplicate register:
```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}'
```
Expected: 409 detail "用户名已存在"

Test login:
```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}' | python -m json.tool
```
Expected: `{"token": "<hex>", "user": {...}}`

Test logout:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -s -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```
Expected: `{"ok":true}`

- [ ] **Step 5: Kill the test server**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 6: Commit**

```bash
git add server/routes/auth.py server/main.py
git commit -m "feat: add auth routes for register, login, logout

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Create user profile route

**Files:**
- Create: `server/routes/users.py`

- [ ] **Step 1: Create users route file**

Create `server/routes/users.py`:

```python
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
```

- [ ] **Step 2: Register users route in main.py**

Edit `server/main.py`. Change the import line:

```python
from server.routes import rooms, ws, auth, users
```

Add the router registration:

```python
app.include_router(users.router)
```

- [ ] **Step 3: Test the endpoint**

Start server, get a token, then call /api/users/me:
```bash
cd server && source .venv/bin/activate && uvicorn server.main:app --port 8000 &
sleep 1

# Register and get token
RESP=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"bob","password":"pass1234"}')
TOKEN=$(echo $RESP | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Call /api/users/me
curl -s http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```
Expected: `{"id": 2, "username": "bob", "total_games": 0, ...}`

Test unauthorized:
```bash
curl -s http://localhost:8000/api/users/me
```
Expected: 401

- [ ] **Step 4: Kill the test server**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 5: Commit**

```bash
git add server/routes/users.py server/main.py
git commit -m "feat: add user profile endpoint GET /api/users/me

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Extend Player model with user_id and pass it when joining

**Files:**
- Modify: `server/models/player.py`
- Modify: `server/routes/rooms.py`

- [ ] **Step 1: Add user_id to Player dataclass**

Edit `server/models/player.py`. Add the `user_id` field and include it in `to_dict()`:

```python
from dataclasses import dataclass, field
import uuid
import secrets
from typing import Optional


@dataclass
class Player:
    nickname: str
    room_id: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    token: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)
    is_host: bool = False
    score: int = 0
    is_connected: bool = True
    user_id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nickname": self.nickname,
            "is_host": self.is_host,
            "score": self.score,
            "is_connected": self.is_connected,
            "user_id": self.user_id,
        }
```

- [ ] **Step 2: Accept user_id in create_room and join_room**

Edit `server/routes/rooms.py`. Update request models and route handlers:

Add `user_id` to `CreateRoomRequest`:
```python
class CreateRoomRequest(BaseModel):
    nickname: str
    mode: str = "classic"
    user_id: int | None = None
```

Add `user_id` to `JoinRoomRequest`:
```python
class JoinRoomRequest(BaseModel):
    nickname: str
    user_id: int | None = None
```

In `create_room`, after `room, player = rm.create_room(req.nickname.strip())`, add:
```python
    if req.user_id is not None:
        player.user_id = req.user_id
```

In `join_room`, after `room, player = rm.join_room(room_id, req.nickname.strip())`, add:
```python
    if req.user_id is not None:
        player.user_id = req.user_id
```

- [ ] **Step 3: Commit**

```bash
git add server/models/player.py server/routes/rooms.py
git commit -m "feat: add optional user_id to Player model and room routes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Update user stats on game end

**Files:**
- Modify: `server/routes/ws.py`

- [ ] **Step 1: Import the stats update function**

Edit `server/routes/ws.py`. Add import at top:

```python
from server.data.db import get_random_question, update_user_stats
```

- [ ] **Step 2: Add stats update logic in end_game handler**

In `ws.py`, find the `elif msg_type == "end_game":` block (around line 450). After `result = game_engine.end_game(room, player_id)`, add stats update logic:

The complete block should become:

```python
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
```

- [ ] **Step 3: Also add stats update for mode 2 detective_correct**

Find the `detective_correct` broadcast block (around line 346-371). After the broadcasts, add the same stats update logic using `result["standings"]`:

After the second `broadcast_to_all` for `phase_change` in the detective_correct handler, add:

```python
                            # Update user stats for registered players
                            for entry in result["standings"]:
                                pid = entry["player_id"]
                                player = room.get_player(pid)
                                if player and player.user_id is not None:
                                    is_winner = (entry == result["standings"][0])
                                    update_user_stats(player.user_id, entry["score"], is_winner)
```

- [ ] **Step 4: Commit**

```bash
git add server/routes/ws.py
git commit -m "feat: update user stats on game end for registered players

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Frontend — auth store and LoginModal

**Files:**
- Modify: `client/src/stores/room.js`
- Create: `client/src/views/LoginModal.vue`

- [ ] **Step 1: Add auth state and methods to room store**

Edit `client/src/stores/room.js`. Add auth-related state, computed properties, and actions.

After `const gameMode = ref('classic')`, add:

```javascript
  // Auth state
  const currentUser = ref(null)
  const authChecked = ref(false)
  const authError = ref('')
  const showLoginModal = ref(false)

  const isLoggedIn = computed(() => currentUser.value !== null)
  const loginToken = computed(() => localStorage.getItem('dolos_user') || '')
```

After the `modeLabel` computed, add:

```javascript
  function initAuth() {
    const token = localStorage.getItem('dolos_user')
    if (!token) {
      authChecked.value = true
      return
    }
    fetch('/api/users/me', {
      headers: { 'Authorization': `Bearer ${token}` },
    })
      .then(resp => {
        if (!resp.ok) {
          localStorage.removeItem('dolos_user')
          return null
        }
        return resp.json()
      })
      .then(user => {
        if (user) {
          currentUser.value = user
        }
        authChecked.value = true
      })
      .catch(() => {
        authChecked.value = true
      })
  }

  async function login(username, password) {
    authError.value = ''
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!resp.ok) {
      const data = await resp.json()
      authError.value = data.detail || '登录失败'
      return false
    }
    const data = await resp.json()
    localStorage.setItem('dolos_user', data.token)
    currentUser.value = data.user
    authError.value = ''
    return true
  }

  async function register(username, password) {
    authError.value = ''
    const resp = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!resp.ok) {
      const data = await resp.json()
      authError.value = data.detail || '注册失败'
      return false
    }
    const data = await resp.json()
    localStorage.setItem('dolos_user', data.token)
    currentUser.value = data.user
    authError.value = ''
    return true
  }

  async function logout() {
    const token = localStorage.getItem('dolos_user')
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        })
      } catch {}
    }
    localStorage.removeItem('dolos_user')
    currentUser.value = null
  }
```

Update the return statement to include the new exports:

```javascript
  return {
    roomId, players, myPlayerId, myToken, phase, hostId, connected, gameMode,
    isHost, playerCount, canStart, isClassic, isWhoIsHonest, modeLabel,
    setRoom, updateFromMessage,
    // Auth
    currentUser, authChecked, authError, showLoginModal, isLoggedIn, loginToken,
    initAuth, login, register, logout,
  }
```

- [ ] **Step 2: Create LoginModal component**

Create `client/src/views/LoginModal.vue`:

```vue
<!-- client/src/views/LoginModal.vue -->
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="login-modal">
      <div class="modal-header">
        <h3>{{ tab === 'login' ? '登录' : '注册' }}</h3>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="tab-bar">
        <button
          :class="{ active: tab === 'login' }"
          @click="tab = 'login'"
        >登录</button>
        <button
          :class="{ active: tab === 'register' }"
          @click="tab = 'register'"
        >注册</button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-form">
        <input
          v-model="username"
          class="input"
          placeholder="用户名"
          maxlength="20"
          required
        />
        <input
          v-model="password"
          class="input"
          type="password"
          placeholder="密码"
          required
        />
        <p v-if="roomStore.authError" class="error">{{ roomStore.authError }}</p>
        <button type="submit" class="btn btn-primary" :disabled="!username.trim() || !password">
          {{ tab === 'login' ? '登录' : '注册' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoomStore } from '../stores/room'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close'])

const roomStore = useRoomStore()
const tab = ref('login')
const username = ref('')
const password = ref('')

async function handleSubmit() {
  let ok
  if (tab.value === 'login') {
    ok = await roomStore.login(username.value.trim(), password.value)
  } else {
    ok = await roomStore.register(username.value.trim(), password.value)
  }
  if (ok) {
    emit('close')
    username.value = ''
    password.value = ''
  }
}
</script>
```

- [ ] **Step 3: Add modal CSS to style.css**

Append to `client/src/style.css`:

```css
/* --- Login modal --- */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.login-modal {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 24px;
  width: 100%;
  max-width: 360px;
  margin: 16px;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.modal-header h3 { font-size: 18px; }
.modal-close {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 20px;
  cursor: pointer;
}
.tab-bar {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.tab-bar button {
  flex: 1;
  padding: 10px;
  border: none;
  background: var(--surface-hover);
  color: var(--text-dim);
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s;
}
.tab-bar button.active {
  background: var(--primary);
  color: #fff;
}
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.modal-form .error {
  margin: 0;
}
```

- [ ] **Step 4: Commit**

```bash
git add client/src/stores/room.js client/src/views/LoginModal.vue client/src/style.css
git commit -m "feat: add auth store and LoginModal component

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Frontend — ProfilePanel component

**Files:**
- Create: `client/src/views/ProfilePanel.vue`

- [ ] **Step 1: Create ProfilePanel component**

Create `client/src/views/ProfilePanel.vue`:

```vue
<!-- client/src/views/ProfilePanel.vue -->
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="login-modal">
      <div class="modal-header">
        <h3>📊 个人档案</h3>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="profile-body">
        <div class="profile-username">{{ roomStore.currentUser?.username }}</div>
        <div class="profile-stats">
          <div class="stat-card">
            <div class="stat-value">{{ roomStore.currentUser?.total_games || 0 }}</div>
            <div class="stat-label">总局数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ roomStore.currentUser?.total_wins || 0 }}</div>
            <div class="stat-label">🥇 夺冠</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ roomStore.currentUser?.total_score || 0 }}</div>
            <div class="stat-label">总得分</div>
          </div>
        </div>
        <div v-if="roomStore.currentUser?.total_games" class="stat-extra">
          场均 {{ (roomStore.currentUser.total_score / roomStore.currentUser.total_games).toFixed(1) }} 分 ·
          胜率 {{ (roomStore.currentUser.total_wins / roomStore.currentUser.total_games * 100).toFixed(0) }}%
        </div>
        <p v-if="roomStore.currentUser?.created_at" class="stat-date">
          注册于 {{ roomStore.currentUser.created_at.slice(0, 10) }}
        </p>

        <button class="btn btn-secondary" @click="handleLogout">🚪 退出登录</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoomStore } from '../stores/room'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close'])

const roomStore = useRoomStore()

async function handleLogout() {
  await roomStore.logout()
  emit('close')
}
</script>
```

- [ ] **Step 2: Add profile CSS to style.css**

Append to `client/src/style.css`:

```css
/* --- Profile panel --- */
.profile-body {
  text-align: center;
}
.profile-username {
  font-size: 22px;
  font-weight: bold;
  margin-bottom: 20px;
  color: var(--primary);
}
.profile-stats {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.stat-card {
  flex: 1;
  background: var(--surface-hover);
  border-radius: 8px;
  padding: 14px 8px;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--accent);
}
.stat-label {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 4px;
}
.stat-extra {
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 8px;
}
.stat-date {
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 16px;
}
```

- [ ] **Step 3: Commit**

```bash
git add client/src/views/ProfilePanel.vue client/src/style.css
git commit -m "feat: add ProfilePanel component with stats display

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Update HomeView and RoomView for auth

**Files:**
- Modify: `client/src/views/HomeView.vue`
- Modify: `client/src/views/RoomView.vue`

- [ ] **Step 1: Add auth controls to HomeView**

Edit `client/src/views/HomeView.vue`.

Add the auth bar before the logo div in the template:

```vue
  <div class="auth-bar">
    <template v-if="roomStore.isLoggedIn && roomStore.currentUser">
      <span class="auth-user" @click="showProfile = true">👤 {{ roomStore.currentUser.username }}</span>
      <button class="btn-auth" @click="showProfile = true">📊</button>
    </template>
    <button v-else class="btn-auth" @click="roomStore.showLoginModal = true">登录 / 注册</button>
  </div>
```

In the `<script setup>`, add:

```javascript
import { ref } from 'vue'

const showProfile = ref(false)
```

Add these components after the `<script setup>` block (or import at the top):

```javascript
import LoginModal from './LoginModal.vue'
import ProfilePanel from './ProfilePanel.vue'
```

Not actually — these need to be in the script block. Update the imports:

```javascript
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import LoginModal from './LoginModal.vue'
import ProfilePanel from './ProfilePanel.vue'
```

Add the modals at the end of the template (before the closing `</div>`):

```vue
    <LoginModal :visible="roomStore.showLoginModal" @close="roomStore.showLoginModal = false" />
    <ProfilePanel :visible="showProfile" @close="showProfile = false" />
```

Add `onMounted` to init auth:

```javascript
onMounted(() => {
  roomStore.initAuth()
  const codeFromUrl = route.params.roomCode
  if (codeFromUrl) {
    roomCode.value = codeFromUrl.toUpperCase()
  }
})
```

Update `createRoom` to pass `user_id`:

```javascript
async function createRoom() {
  if (!nickname.value.trim()) return
  error.value = ''
  try {
    sessionStorage.removeItem('dolos_session')
    const body = {
      nickname: nickname.value.trim(),
      mode: selectedMode.value,
    }
    if (roomStore.currentUser) {
      body.user_id = roomStore.currentUser.id
    }
    const resp = await fetch('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
```

Update `joinRoom` to pass `user_id`:

```javascript
  const body = {
    nickname: nickname.value.trim(),
  }
  if (roomStore.currentUser) {
    body.user_id = roomStore.currentUser.id
  }
  const resp = await fetch(`/api/rooms/${roomCode.value.trim().toUpperCase()}/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
```

- [ ] **Step 2: Add auth CSS to style.css**

Append:

```css
/* --- Auth bar --- */
.auth-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.auth-user {
  font-size: 14px;
  color: var(--accent);
  cursor: pointer;
  font-weight: 600;
}
.btn-auth {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-dim);
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  transition: border-color 0.2s, color 0.2s;
}
.btn-auth:hover {
  border-color: var(--primary);
  color: var(--text);
}
```

- [ ] **Step 3: Update RoomView — auto-fill nickname for logged-in users**

Edit `client/src/views/RoomView.vue`. No changes needed for RoomView currently — the nickname was already entered on HomeView. The room view only needs auth init called on mount if not already done. Add to the `onMounted`:

```javascript
onMounted(() => {
  roomStore.initAuth()
  const roomId = route.params.id
  connect(roomId, roomStore.myPlayerId, roomStore.myToken)
})
```

- [ ] **Step 4: Pre-fill nickname when logged in on HomeView**

Edit `client/src/views/HomeView.vue`. In `onMounted`, after `roomStore.initAuth()`, add a watcher or direct assignment:

Actually, the simplest approach: after `initAuth()` resolves, if the user is logged in and nickname is empty, pre-fill it. But `initAuth` is async. Let's use a watch in the store instead — or better, just check in the onMounted after a short delay:

```javascript
onMounted(async () => {
  roomStore.initAuth()
  const codeFromUrl = route.params.roomCode
  if (codeFromUrl) {
    roomCode.value = codeFromUrl.toUpperCase()
  }
  // Pre-fill nickname for logged-in users
  await new Promise(r => setTimeout(r, 200))
  if (roomStore.currentUser && !nickname.value) {
    nickname.value = roomStore.currentUser.username
  }
})
```

- [ ] **Step 5: Commit**

```bash
git add client/src/views/HomeView.vue client/src/views/RoomView.vue client/src/style.css
git commit -m "feat: integrate auth into HomeView and RoomView

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Backend tests

**Files:**
- Create: `server/tests/test_auth.py`

- [ ] **Step 1: Write tests for auth and user profile**

Create `server/tests/test_auth.py`:

```python
import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.data.db import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


class TestAuth:
    def test_register_success(self):
        resp = client.post("/api/auth/register", json={
            "username": "testplayer",
            "password": "secret123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) == 32
        assert data["user"]["username"] == "testplayer"
        assert data["user"]["total_games"] == 0

    def test_register_duplicate_username(self):
        client.post("/api/auth/register", json={
            "username": "uniqueuser",
            "password": "pass1234",
        })
        resp = client.post("/api/auth/register", json={
            "username": "uniqueuser",
            "password": "pass1234",
        })
        assert resp.status_code == 409

    def test_register_short_username(self):
        resp = client.post("/api/auth/register", json={
            "username": "a",
            "password": "pass1234",
        })
        assert resp.status_code == 400

    def test_register_short_password(self):
        resp = client.post("/api/auth/register", json={
            "username": "validuser",
            "password": "ab",
        })
        assert resp.status_code == 400

    def test_login_success(self):
        client.post("/api/auth/register", json={
            "username": "loginuser",
            "password": "mypassword",
        })
        resp = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "mypassword",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "loginuser"

    def test_login_wrong_password(self):
        client.post("/api/auth/register", json={
            "username": "pwuser",
            "password": "correct",
        })
        resp = client.post("/api/auth/login", json={
            "username": "pwuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = client.post("/api/auth/login", json={
            "username": "nobody",
            "password": "whatever",
        })
        assert resp.status_code == 401

    def test_logout(self):
        resp = client.post("/api/auth/register", json={
            "username": "logoutuser",
            "password": "pass1234",
        })
        token = resp.json()["token"]
        resp2 = client.post("/api/auth/logout", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp2.status_code == 200
        assert resp2.json() == {"ok": True}

        # Token should be invalid after logout
        resp3 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp3.status_code == 401

    def test_get_me_success(self):
        resp = client.post("/api/auth/register", json={
            "username": "meuser",
            "password": "pass1234",
        })
        token = resp.json()["token"]
        resp2 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp2.status_code == 200
        assert resp2.json()["username"] == "meuser"

    def test_get_me_unauthorized(self):
        resp = client.get("/api/users/me")
        assert resp.status_code == 401

    def test_login_updates_token(self):
        resp = client.post("/api/auth/register", json={
            "username": "tokenuser",
            "password": "pass1234",
        })
        old_token = resp.json()["token"]
        resp2 = client.post("/api/auth/login", json={
            "username": "tokenuser",
            "password": "pass1234",
        })
        new_token = resp2.json()["token"]
        assert old_token != new_token

        # Old token should now be invalid
        resp3 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {old_token}",
        })
        assert resp3.status_code == 401

    def test_login_empty_username(self):
        resp = client.post("/api/auth/login", json={
            "username": "",
            "password": "something",
        })
        assert resp.status_code == 400

    def test_new_login_replaces_token(self):
        """After fresh login, old token is invalidated."""
        resp = client.post("/api/auth/register", json={
            "username": "replacetoken",
            "password": "pass1234",
        })
        token1 = resp.json()["token"]

        # Login again
        resp2 = client.post("/api/auth/login", json={
            "username": "replacetoken",
            "password": "pass1234",
        })
        token2 = resp2.json()["token"]

        # token2 should work
        resp3 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token2}",
        })
        assert resp3.status_code == 200

        # token1 should be invalid (replaced by new login)
        resp4 = client.get("/api/users/me", headers={
            "Authorization": f"Bearer {token1}",
        })
        assert resp4.status_code == 401
```

- [ ] **Step 2: Run the tests**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/test_auth.py -v
```
Expected: all 13 tests pass.

- [ ] **Step 3: Run all existing tests to ensure no regressions**

```bash
cd server && source .venv/bin/activate && python -m pytest tests/ -v
```
Expected: all existing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add server/tests/test_auth.py
git commit -m "test: add auth and user profile API tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: End-to-end manual verification

- [ ] **Step 1: Start server and dev frontend**

```bash
# Terminal 1: server
cd server && source .venv/bin/activate && uvicorn server.main:app --reload --port 8000

# Terminal 2: client
cd client && npm run dev
```

- [ ] **Step 2: Verify registration flow**

1. Open http://localhost:5173
2. Click "登录 / 注册" in top right
3. Register with username "alice" and password "pass1234"
4. Verify "alice" appears in the auth bar
5. Create a room — verify nickname is pre-filled as "alice"
6. Open a new tab — verify still logged in as "alice"
7. Click profile → verify stats show 0 games
8. Click "退出登录" → verify auth bar says "登录 / 注册"
9. Open a new tab — verify NOT logged in

- [ ] **Step 3: Verify anonymous play still works**

1. Without logging in, create a room with nickname "guest"
2. Verify it works exactly as before

- [ ] **Step 4: Verify stats update after game**

1. Login as "alice"
2. Create a room in classic mode
3. Open a second browser (or incognito) as anonymous "bob", join same room
4. Play one full round, host ends game
5. Open profile → verify total_games = 1, and score/wins updated

- [ ] **Step 5: Cleanup test database**

```bash
rm server/data/dolos.db
```
(It will be recreated on next startup with fresh data)

- [ ] **Step 6: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: adjustments from manual verification

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
