# Dolos（瞎掰王）— 游戏设计文档

> 多人实时派对游戏，基于 Balderdash/瞎掰王规则。玩家通过手机/PC 浏览器连接，一法官出题、其他人编假定义、全员投票猜真。

## 1. 游戏规则

- **最少 4 人**开局
- **回合流程**（法官手动控场，无强制计时器）：
  1. **抽题** — 法官从题库抽取一道题
  2. **编答案** — 非-法官玩家各自编造一条假定义，提交后不可修改
  3. **收答案** — 法官确认后触发投票
  4. **投票** — 所有玩家看混排的 A/B/C/D 等选项，投出认为是真答案的一项
  5. **揭晓** — 公布真答案 + 本回合得分 + 累计排行
  6. **轮转** — 法官轮换给下一位玩家，进入下一回合
- **结束条件**：无限回合（派对游戏风格），房主在任意回合结束时点击「结束游戏」，立即结算最终排名。其他玩家也可以提议结束，由房主最终决定
- **计分规则**：
  - 投中真答案：+2 分
  - 编的假答案骗到别人投票：+1 分/每人
  - 法官出题且无人猜中真答案：+3 分

## 2. 技术选型

| 层 | 技术 | 理由 |
|------|------|------|
| 后端 | Python FastAPI | 原生 WebSocket 支持，异步性能好 |
| 前端 | Vue 3 + Vite | 轻量、移动端友好、内置动画 |
| 状态管理 | Pinia | Vue 3 官方推荐，够用不重 |
| 实时通信 | WebSocket | 全双工低延迟，原生支持 |
| 持久化 | SQLite | 零依赖，存题目 + 可选用户 |
| 运维 | Cloudflare Tunnel | 免费公网穿透，本地部署即可 |

## 3. 架构

```
浏览器 (Vue 3 + Pinia)
  │
  ├── HTTP (创建/加入房间)
  │  POST /api/rooms → create
  │  POST /api/rooms/:id/join → join
  │  GET  /api/rooms/:id → info
  │
  └── WebSocket (游戏全程)
       ws://host/ws/{room_id}?player_id=xxx&token=xxx

FastAPI 服务器
  ├── RoomManager   — 房间 CRUD、玩家进出
  ├── GameEngine    — 状态机、计分
  ├── WSManager     — 连接管理、广播
  ├── QuestionBank  — 题目存取（SQLite）
  └── 存储：内存（房间/游戏状态）+ SQLite（题目/用户）
```

## 4. 数据模型

```
Player
  id: UUID          nickname: str      room_id: str
  is_host: bool     score: int         is_connected: bool

Room
  id: str (4位码)   players: list[Player]
  config: {max_players: 6}
  phase: GamePhase   current_game: Game | None

Game
  rounds: list[Round]         current_round_index: int
  judge_index: int            phase: GamePhase

Round
  question: Question
  judge_id: str
  fake_answers: dict[player_id → text]
  shuffled_answers: list[{text, is_real, player_id}]
  votes: dict[voter_id → answer_index]
  scores_awarded: dict[player_id → int]

Question
  id: int           term: str            real_definition: str
  category: str     source: "builtin"|"player"
  contributor_id: str | None
```

## 5. 游戏状态机

```
WAITING ──(房主 start)──▶ DRAWING ──(法官 draw)──▶ ANSWERING
                                                      │
                                              (法官 collect)
                                                      ▼
ROUND_END ◀──(揭晓结束)── REVEALING ◀──(法官 end_vote)── VOTING
    │
    ├──(还有下一轮)──▶ DRAWING
    └──(结束)────────▶ GAME_OVER
```

## 6. WebSocket 消息协议

### 客户端 → 服务端

| type | payload | 说明 |
|------|---------|------|
| `submit_answer` | `{text: str}` | 提交假定义 |
| `cast_vote` | `{answer_index: int}` | 投票 |
| `judge_action` | `{action: "draw"\|"collect"\|"end_vote"}` | 法官控场 |
| `start_game` | `{}` | 房主开始（≥4人） |

### 服务端 → 客户端

| type | payload | 说明 |
|------|---------|------|
| `room_update` | `{players[], host_id}` | 玩家进出广播 |
| `phase_change` | `{phase, judge_id, question?}` | 阶段切换 |
| `vote_options` | `{options: [{index, text}]}` | 混排投票选项 |
| `reveal` | `{correct_index, scores[], standings[]}` | 揭晓结果 |
| `round_start` | `{round_num, judge_id}` | 新回合 |
| `game_over` | `{final_scores[]}` | 最终排名 |
| `error` | `{message}` | 错误提示 |

## 7. 前端路由 & 视图

| 路由 | 视图 | 内容 |
|------|------|------|
| `/` | HomeView | 输入昵称 → 创建房间 / 加入房间（房间码） |
| `/room/:id` | RoomView | 玩家列表、房间码展示、房主配置+开始按钮 |
| `/room/:id/play` | GameView | 根据 phase 切换：答题面板 / 投票面板 / 揭晓面板 / 法官面板 |

GameView 内根据 `phase` 条件渲染的子组件：
- `AnswerInput.vue` — 编答案阶段
- `VotingPanel.vue` — 投票阶段
- `RevealPanel.vue` — 揭晓结果
- `JudgePanel.vue` — 法官浮动控场栏
- `ScoreBoard.vue` — 常驻顶栏或侧栏计分板
- `PlayerList.vue` — 在线玩家状态

PC 端适配：内容区最大宽度 480px 居中，左右留空。

## 8. 题目库

- **内置**：200-300 题，JSON 文件存储，服务启动导入 SQLite
- **格式**：`{term, definition, category}`，分类含成语、冷知识、网络梗、科技术语
- **玩家贡献**：房间内可提交新题，标记 source=player，经房主审核后入库

## 9. 边界处理

| 场景 | 处理 |
|------|------|
| 玩家断线 | 标记 `is_connected=false`，同 ID + token 可重连恢复 |
| 法官断线 | 自动轮转给下一玩家，广播通知 |
| 投票时某人未投 | 法官 `end_vote` 时跳过，该玩家本回合不得分 |
| 房间人走光 | 清理房间 |
| 低于 4 人 | 游戏暂停，等待新玩家或房主结束 |

## 10. 目录结构

```
Dolos/
├── server/
│   ├── main.py
│   ├── config.py
│   ├── models/       # player.py, room.py, question.py
│   ├── managers/     # room_manager.py, game_engine.py, ws_manager.py
│   ├── routes/       # rooms.py, ws.py
│   ├── data/         # questions.json, db.py
│   └── tests/        # test_room.py, test_game.py, test_ws.py
├── client/
│   ├── index.html
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.js, App.vue, router.js
│   │   ├── stores/       # room.js, game.js
│   │   ├── composables/  # useWebSocket.js
│   │   ├── views/        # HomeView.vue, RoomView.vue, GameView.vue
│   │   └── components/   # PlayerList, AnswerInput, VotingPanel,
│   │                      # RevealPanel, ScoreBoard, JudgePanel
├── shared/
│   └── constants.py
└── docs/
    └── superpowers/specs/
```

## 11. 测试策略

| 范围 | 内容 | 工具 |
|------|------|------|
| `game_engine` 单元 | 状态机每阶段切换、计分逻辑、边界情况 | pytest |
| `room_manager` 单元 | 房间 CRUD、玩家进出、并发 | pytest |
| WebSocket 集成 | 完整一轮：4 玩家连接→编答案→投票→揭晓 | pytest-asyncio + TestClient |
| Pinia stores | 状态对服务端消息的响应 | Vitest |
| 关键组件 | VotingPanel、AnswerInput 交互逻辑 | Vitest + Vue Test Utils |
| E2E | 暂不做，UI 稳定后追加 | Playwright（未来） |

## 12. 实现顺序

```
Phase 1 — 后端骨架
  models → room_manager → game_engine（+ 测试）→ HTTP routes → WebSocket

Phase 2 — 前端骨架
  Vite 脚手架 → HomeView → RoomView → WebSocket 连接

Phase 3 — 游戏核心
  GameView 组件逐步实现（按阶段）

Phase 4 — 打磨
  题目库导入 → 断线重连 → 过渡动画 → 手机实测
```

## 13. 部署

- **开发**：`uvicorn server.main:app --reload`，`npm run dev`，`localhost`
- **外网分享**：Cloudflare Tunnel — `cloudflared tunnel --url http://localhost:8000`，获得公网 URL
- 无需云服务器
