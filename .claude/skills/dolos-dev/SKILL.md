---
name: dolos-dev
description: >
  当你对 /home/quasrain/repos/Dolos 目录下的任何文件进行修改、编辑、新增、删除、重构、修复 bug、添加功能、编写测试、调整配置、更新文档时，必须使用此 skill。
  只要工作目录或操作涉及 Dolos 仓库，无论任务大小（改一行代码、修一个 typo、调整样式、重构架构），都必须先加载此 skill 获取项目上下文和开发规范。
  本项目是一个多人实时派对游戏（瞎掰王），后端 Python FastAPI + WebSocket + SQLite，前端 Vue 3 + Vite + Pinia。有经典模式和谁是老实人两种游戏模式。
---

# Dolos 项目开发指南

## 核心理念

Dolos 是一个**实时多人 WebSocket 游戏**。所有游戏状态由服务端内存中的单例对象管理，客户端通过 WebSocket 接收状态变更。理解这一点是正确开发的关键：

- **服务端是唯一真相源**：房间、玩家、回合、分数全部在 `server/main.py` 的全局单例中
- **客户端是"视图"**：Vue 组件根据 `phase` 切换渲染，不持有游戏逻辑
- **WebSocket 是神经系统**：所有游戏操作通过 WebSocket 消息触发，结果通过广播同步

## 分支策略

- **`main`** — 主要开发分支，日常开发在此分支上进行
- **`release`** — 发布分支，稳定版本从这里发布
- **新功能** — 必须从 `main` 拉出新分支开发，不允许直接在 `main` 或 `release` 上提交
- **合入规则** — 向 `main` 或 `release` 合入代码必须通过 Pull Request，**由用户确认后才能合入**，不允许直接 push 或 merge

### 开发流程

```
main ─── feature/xxx ─── PR ──→ main ─── PR ──→ release
  │                            │
  └── 日常开发基础               └── 需用户审批
```

1. 从 `main` 创建 feature 分支：`git checkout -b feature/xxx main`
2. 在 feature 分支上开发和提交
3. 开发完成后，向 `main` 发起 PR，等用户审批合入
4. 准备发布时，从 `main` 向 `release` 发起 PR，等用户审批合入

**重要**：除非用户明确指示，否则**不要自行合并任何 PR**。所有合入操作必须等待用户确认。

## 架构速览

```
浏览器                    服务端
┌──────────┐  WebSocket   ┌─────────────────────────┐
│ Vue 3 App │◄────────────►│ FastAPI                  │
│ Pinia     │  JSON msgs   │  ├─ ws.py (消息路由)      │
│ HashRouter│              │  ├─ game_engine.py (逻辑)  │
└──────────┘              │  ├─ room_manager.py (房间) │
                          │  ├─ ws_manager.py (连接)   │
                          │  └─ data/db.py (SQLite)    │
                          └─────────────────────────┘
```

### 数据流（以经典模式提交答案为例）

```
玩家点击提交 → WebSocket send → ws.py 收到 submit_answer
  → game_engine.submit_answer() 写入 round.fake_answers
  → 检查是否全员提交 → 自动调用 judge_collect()
  → ws_manager.broadcast_to_all() 发送 vote_options
  → 所有客户端 game store 更新 phase='voting' → VotingPanel 渲染
```

关键原则：**永远在 game_engine 中修改状态，在 ws.py 中做消息路由，在 ws_manager 中做广播**。不要在 ws.py 里写游戏逻辑。

## 项目结构

```
Dolos/
├── server/
│   ├── main.py              # FastAPI app + 全局单例
│   ├── config.py             # 常量: ROOM_CODE_LENGTH, MAX_PLAYERS(8), MIN_PLAYERS(2)
│   ├── models/               # dataclass: Player, Room, Game, Round, Question
│   ├── managers/             # 核心逻辑层 (无状态或操作传入的 state)
│   │   ├── game_engine.py    # 游戏流程: start_game → judge_draw → submit_answer → cast_vote → _end_vote → next_round
│   │   ├── room_manager.py   # 房间生命周期: create/join/leave/reconnect
│   │   └── ws_manager.py     # WebSocket 连接登记 + broadcast/send_to_player
│   ├── routes/
│   │   ├── rooms.py          # REST: POST /api/rooms, POST /api/rooms/{id}/join, GET /api/rooms/{id}
│   │   └── ws.py             # WebSocket /ws/{room_id}?player_id=&token= 消息分发
│   ├── data/
│   │   ├── db.py             # SQLite: init_db, get_random_question, add_question
│   │   └── questions.json    # 内置题库 (~50题)
│   └── tests/                # pytest: test_game_engine, test_room_manager, test_ws, test_db, test_models
├── client/
│   ├── src/
│   │   ├── stores/
│   │   │   ├── room.js       # 房间状态 (playerId, token 存 sessionStorage)
│   │   │   └── game.js       # 游戏状态 (phase, voteOptions, revealData, mode2 roles)
│   │   ├── composables/
│   │   │   └── useWebSocket.js  # WS 连接管理 (自动重连 2s)
│   │   ├── views/
│   │   │   ├── HomeView.vue   # 创建/加入房间
│   │   │   ├── RoomView.vue   # 等待大厅 (玩家列表 + 开始按钮)
│   │   │   └── GameView.vue   # 游戏主界面 (phase 驱动组件渲染)
│   │   └── components/
│   │       ├── AnswerInput.vue         # 编答案 (mode2 老实人预填不可编辑)
│   │       ├── JudgePanel.vue          # 法官控制台 (仅经典模式+法官可见)
│   │       ├── VotingPanel.vue         # 投票面板
│   │       ├── RevealPanel.vue         # 揭晓结果
│   │       ├── ScoreBoard.vue          # 顶部积分榜
│   │       ├── PlayerList.vue          # 玩家列表
│   │       └── DetectiveGuessPanel.vue # mode2 大聪明猜人面板
│   └── vite.config.js
└── CLAUDE.md                # 项目级 Claude 上下文
```

## 游戏阶段机 (GamePhase)

两个模式共用阶段枚举，但流转路径不同：

### 经典模式
```
WAITING → DRAWING → ANSWERING → VOTING → REVEALING → (就绪) → DRAWING → ...
                                                         └→ GAME_OVER
```

### 谁是老实人 (mode 2)
```
WAITING → DRAWING(系统自动) → ANSWERING → VOTING(仅大聪明) → REVEALING → (就绪) → DRAWING → ...
                                                                       └→ GAME_OVER
```

阶段转换**只在 game_engine.py 中发生**：
- `room.phase = GamePhase.XXX` 是唯一的状态变更方式
- ws.py 调用 engine 方法后，通过 `phase_change` 消息广播新阶段

## 开发模式

### 添加新的 WebSocket 消息类型

需要改 4 个地方：

1. **game_engine.py** — 添加业务逻辑方法，raise `GameError` 表示失败
2. **ws.py** — 在消息循环中添加 `elif msg_type == "xxx":` 分支，调用 engine，广播结果
3. **client game store** (`stores/game.js`) — 在 `updateFromMessage` 中添加 `case 'xxx':` 处理新消息类型
4. **client 组件** — 根据新状态渲染 UI

### 添加新的游戏模式

若要添加第三个模式：

1. **models/room.py** — 在 `GameMode` 枚举中添加新值
2. **game_engine.py** — 添加模式专属方法（参考 `mode2_start_round`, `submit_detective_guess`），在现有方法中通过 `if game.mode ==` 分支
3. **ws.py** — 在消息处理中添加新模式分支（参考 `WHO_IS_HONEST` 分支）
4. **config.py** — 如有新的常量限制
5. **client game store** — 添加新模式的状态字段
6. **client views/components** — 添加新模式的 UI（通过 `roomStore.isXxxMode` 条件渲染）
7. **HomeView.vue** — 添加模式选择
8. **更新 docs/游戏说明.md**

### 修改计分逻辑

计分逻辑在 `game_engine.py` 的两个位置：
- `_calculate_scores()` — 经典模式批量计分（投票结束调用）
- `cast_vote()` mode2 分支 — 谁是老实人模式计分（大聪明选对时）

修改计分时注意：
- `scores_awarded` 字典记录每人本回合得分（用于前端显示明细）
- `player.score` 是累计分

## WebSocket 消息协议

### 客户端 → 服务端

| type | 字段 | 说明 |
|------|------|------|
| `start_game` | `mode` | 房主开始游戏 |
| `judge_action` | `action` ("draw"/"collect"/"end_vote") | 法官操作 |
| `submit_answer` | `text` | 提交假答案 |
| `cast_vote` | `answer_index` | 投票 |
| `ready_next_round` | — | 就绪进入下一轮 |
| `end_game` | — | 房主结束游戏 |

### 服务端 → 客户端

| type | 触发时机 | 接收者 |
|------|----------|--------|
| `room_update` | 玩家进出/状态变更 | 全员 |
| `phase_change` | 阶段变更 | 全员 |
| `judge_info` | 法官抽题后 | 仅法官 |
| `role_info` | mode2 角色分配 | 仅本人 |
| `answer_submitted` | 提交答案确认 | 仅提交者 |
| `answer_progress` | 提交进度更新 | 仅法官 |
| `vote_options` | 进入投票 | 投票者 |
| `vote_cast` | 投票确认 | 仅投票者 |
| `vote_wrong` | mode2 大聪明选错 | 仅大聪明 |
| `detective_retry` | mode2 大聪明重试 | 非大聪明玩家 |
| `reveal` | 经典模式揭晓 | 全员 |
| `detective_correct` | mode2 大聪明选对 | 全员 |
| `ready_progress` | 就绪进度更新 | 全员 |
| `round_start` | 新一轮开始 | 全员 |
| `game_over` | 游戏结束 | 全员 |
| `state_sync` | 重连时状态恢复 | 仅重连者 |
| `error` | 操作失败 | 仅操作者 |

### 消息设计原则

- **私密信息走单播** (`send_to_player`)：角色分配、法官看到的真定义
- **公共状态走广播** (`broadcast_to_all`)：阶段变更、投票结果
- **敏感字段服务端过滤**：`Player.to_dict()` 不包含 `token`
- 新增消息类型时，确保不会泄露不应公开的信息（如 mode2 中非大聪明玩家不应看到答案作者）

## 前端约定

### Store 职责

```
room store (stores/room.js)
  ├── 房间元信息: roomId, players, hostId, phase, gameMode
  ├── 持久化: myPlayerId, myToken → sessionStorage (刷新不丢)
  └── 计算属性: isHost, canStart, isClassic, isWhoIsHonest

game store (stores/game.js)
  ├── 经典模式: questionTerm, judgeId, voteOptions, revealData
  ├── mode2: myRole, roleDefinition, detectiveWrongAnswerIndices
  ├── 通用: standings, readyCount, readyPlayerIds
  └── updateFromMessage(): 统一的消息分发入口
```

### 组件渲染逻辑

`GameView.vue` 通过 `v-if` 按 phase + mode + role 组合条件渲染：

```vue
<!-- 经典模式非-法官编答案 -->
<AnswerInput v-if="phase==='answering' && isClassic && !isJudge" />
<!-- mode2 非-大聪明编答案 -->
<AnswerInput v-if="phase==='answering' && isWhoIsHonest && !isDetective" />
<!-- 大聪明旁观 -->
<div v-if="phase==='answering' && isWhoIsHonest && isDetective">等待中...</div>
```

添加新 UI 时遵循此模式。

### sessionStorage 持久化

玩家身份通过 `sessionStorage` 持久化：
- Key: `dolos_session`
- Value: `{ roomId, myPlayerId, myToken }`
- 页面刷新后自动恢复，WebSocket 重连时用相同身份验证

## 服务端约定

### 全局单例

```python
# server/main.py — 三个全局单例，ws.py 通过 get_managers() 延迟导入获取
room_manager = RoomManager()   # dict[room_id → Room]
game_engine = GameEngine()     # 无状态，接收 room 参数操作
ws_manager = WSManager()       # dict[room_id → dict[player_id → WebSocket]]
```

延迟导入（避免循环依赖）模式：
```python
def get_managers():
    from server.main import room_manager, game_engine, ws_manager
    return room_manager, game_engine, ws_manager
```

### 错误处理

所有游戏逻辑错误通过 `GameError` 及其子类抛出：
- `InvalidPhaseError` — 当前阶段不允许此操作
- `NotHostError` — 非房主操作
- `NotJudgeError` — 非法官操作
- `NotEnoughPlayersError` — 人数不足
- `RoomNotFoundError`, `RoomInGameError`, `RoomFullError`, `RoomNicknameTakenError` — 房间操作错误

ws.py 统一捕获 `GameError` 并返回 `{"type": "error", "message": str(e)}` 给操作者。

### 题目管理

- 内置题库: `server/data/questions.json` (JSON 数组)
- 首次启动自动导入 SQLite (`data/dolos.db`)
- `get_random_question()` 用 `ORDER BY RANDOM()` 随机取题
- `add_question()` 支持玩家投稿（`source='player'`）

## 测试

### 运行测试

```bash
cd server && source .venv/bin/activate && python -m pytest tests/ -v
```

### 测试结构

```
server/tests/
├── test_game_engine.py    # 核心游戏逻辑测试 (最全面)
├── test_room_manager.py   # 房间创建/加入/重连
├── test_ws.py             # WebSocket 集成测试
├── test_db.py             # 数据库操作
└── test_models.py         # 模型创建和 to_dict
```

### 编写测试的模式

`test_game_engine.py` 提供了标准的测试辅助方法：

```python
def make_room_with_players(n=4):
    """创建带有 n 个在线玩家的测试房间"""
    room = Room(id="TEST")
    for i in range(n):
        p = Player(nickname=f"玩家{i+1}")
        room.players.append(p)
    room.host_id = room.players[0].id
    room.players[0].is_host = True
    return room

def make_question():
    return Question(id=1, term="测试题", real_definition="这是真定义")
```

**重要**：按照 [[feedback_ci]] 记忆，每次新增模块必须同步更新 CI test/coverage 步骤。

## 常见开发任务

### 修改最少玩家数

1. `server/config.py` 改 `MIN_PLAYERS`
2. 如果也要改前端提示，更新对应组件

### 修改房间码长度/字符集

1. `server/config.py` 改 `ROOM_CODE_LENGTH` 或 `ROOM_CODE_CHARS`
2. 不需要改客户端（客户端只展示不验证）

### 给经典模式增加自动推进

当前模式：法官手动控场。完全自动化思路：
1. 在 `ws.py` 的 `submit_answer` 处理中已有自动 collect 逻辑
2. 在 `cast_vote` 处理中已有自动 end_vote 逻辑
3. 增加新的自动步骤：用 `asyncio.create_task` + `asyncio.sleep` 延迟自动推进

### 添加计时器

1. 服务端用 `asyncio` 管理计时
2. 通过 WebSocket 广播剩余时间
3. 前端显示倒计时，超时自动操作

## 部署

Render 自动部署（`render.yaml`）：
1. `pip install -r requirements.txt`
2. `cd client && npm install && npm run build`
3. `uvicorn server.main:app --host 0.0.0.0 --port $PORT`

生产环境 FastAPI 直接 serve `client/dist/` 下的静态文件。

## 文档

- `CLAUDE.md` — 项目概览 (Claude 自动加载)
- `README.md` — 对外 README
- `docs/游戏说明.md` — 完整游戏规则说明书
- `docs/superpowers/` — 设计文档和 specs

修改游戏规则时，同步更新 `docs/游戏说明.md` 中的相关章节。
