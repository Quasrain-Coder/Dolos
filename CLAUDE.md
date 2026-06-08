# Dolos — 瞎掰王

多人实时派对游戏。一法官出题，其他人编假定义，全员投票猜真相。

## 技术栈

- **后端**: Python 3.11+ / FastAPI / WebSocket / SQLite
- **前端**: Vue 3 (Composition API) / Vite / Pinia / Vue Router (hash mode)
- **部署**: Render (render.yaml)，前端 build 后由 FastAPI 直接 serve

## 项目结构

```
Dolos/
├── server/
│   ├── main.py              # FastAPI app 入口，全局单例 (room_manager, game_engine, ws_manager)
│   ├── config.py             # 常量: ROOM_CODE_LENGTH, MAX_PLAYERS, MIN_PLAYERS, 题目分类
│   ├── requirements.txt      # fastapi, uvicorn, pydantic
│   ├── models/
│   │   ├── __init__.py       # 导出所有模型
│   │   ├── player.py         # Player dataclass (id, nickname, token, score, is_host, is_connected)
│   │   ├── room.py           # Room, Game, Round dataclasses + GamePhase/GameMode 枚举
│   │   └── question.py       # Question dataclass
│   ├── managers/
│   │   ├── game_engine.py    # 核心游戏逻辑: 开始/抽题/提交答案/投票/计分/下一轮
│   │   ├── room_manager.py   # 房间 CRUD: 创建/加入/离开/重连
│   │   └── ws_manager.py     # WebSocket 连接追踪 + 广播/单播
│   ├── routes/
│   │   ├── rooms.py          # REST API: POST /api/rooms, POST /api/rooms/{id}/join, GET /api/rooms/{id}
│   │   └── ws.py             # WebSocket /ws/{room_id} — 游戏消息协议
│   ├── data/
│   │   ├── db.py             # SQLite 操作: init_db, get_random_question, add_question
│   │   └── questions.json    # 内置题库
│   └── tests/                # pytest 测试
├── client/
│   ├── src/
│   │   ├── main.js           # Vue app 入口
│   │   ├── App.vue           # 根组件
│   │   ├── router.js         # 路由: /, /join/:roomCode, /room/:id, /room/:id/play
│   │   ├── style.css         # 全局样式
│   │   ├── stores/
│   │   │   ├── room.js       # Pinia store: 房间状态、sessionStorage 持久化
│   │   │   └── game.js       # Pinia store: 游戏状态、阶段管理
│   │   ├── composables/
│   │   │   └── useWebSocket.js  # WebSocket 连接/重连/消息分发
│   │   ├── views/
│   │   │   ├── HomeView.vue   # 首页: 创建/加入房间
│   │   │   ├── RoomView.vue   # 等待房间: 玩家列表、开始游戏
│   │   │   └── GameView.vue   # 游戏主界面: 阶段驱动渲染
│   │   └── components/
│   │       ├── AnswerInput.vue         # 编答案输入
│   │       ├── JudgePanel.vue          # 法官面板: 抽题/收答案/结束投票
│   │       ├── VotingPanel.vue         # 投票面板
│   │       ├── RevealPanel.vue         # 揭晓面板
│   │       ├── ScoreBoard.vue          # 积分榜
│   │       ├── PlayerList.vue          # 玩家列表
│   │       └── DetectiveGuessPanel.vue # 谁是老实人: 大聪明猜测面板
│   ├── index.html
│   ├── vite.config.js
│   └── package.json          # vue 3.4, vue-router 4.3, pinia 2.1, vite 5.2
├── render.yaml               # Render 部署配置
└── requirements.txt          # 根目录 (Render build 用)
```

## 游戏模式

### 经典模式 (classic)
1. **WAITING** → 房主开始游戏
2. **DRAWING** → 法官抽题（第一轮房主做法官，之后轮转）
3. **ANSWERING** → 非法官玩家编假答案，全员提交后自动收答案
4. **VOTING** → 所有玩家（含法官出题的真答案）混排后投票，全员投完自动开票
5. **REVEALING** → 揭晓正确答案 + 计分，全员点"就绪"进入下一轮
6. 计分: 猜对 +2，骗到人 +1/人，法官无人猜中 +3

### 谁是老实人 (who_is_honest)
1. **DRAWING** → 系统自动抽题并分配角色 (honest/detective/bluffer)
2. **ANSWERING** → 老实人和瞎掰人编答案，大聪明旁观
3. **VOTING** → 大聪明从混排答案中投票选真答案，选错可重试
4. **REVEALING** → 选对后揭晓 → 全员就绪 → 下一轮重新抽题分配角色

## WebSocket 消息协议

客户端→服务端: `start_game`, `judge_action` (draw/collect/end_vote), `submit_answer`, `cast_vote`, `ready_next_round`, `end_game`
服务端→客户端: `room_update`, `phase_change`, `judge_info`, `role_info`, `vote_options`, `vote_cast`, `vote_wrong`, `reveal`, `detective_correct`, `detective_retry`, `ready_progress`, `round_start`, `game_over`, `state_sync`, `error`

## 关键约定

- 玩家通过 `sessionStorage` 持久化 session (`player_id`, `token`)，刷新页面可重连
- 房间码由 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` 生成 (去掉了易混淆的 0/O/1/I)
- 房主掉线时自动转移给第一个在线玩家
- 生产环境 FastAPI serve `client/dist/` 下的前端构建产物
- CORS: 开发环境允许全部，生产环境通过 `ALLOW_ORIGINS` 环境变量控制

## 常用命令

```bash
# 后端
cd server && source .venv/bin/activate && uvicorn server.main:app --reload --port 8000

# 前端
cd client && npm run dev

# 测试
cd server && source .venv/bin/activate && python -m pytest tests/ -v

# 外网分享
cloudflared tunnel --url http://localhost:8000

# 前端构建
cd client && npm run build
```
