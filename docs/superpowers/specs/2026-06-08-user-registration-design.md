# 用户注册与个人档案 — 设计文档

日期: 2026-06-08

## 概述

为 Dolos 添加用户注册/登录功能和个人战绩档案。注册为可选——保留匿名快速加入，同时提供升级路径。

## 认证机制

- token 模式：随机字符串（`secrets.token_hex(16)`），与现有匿名 token 格式一致
- 注册/登录成功后返回 token，客户端存 `localStorage`（跨标签页、跨 session 持久）
- 登出时清掉服务端 token + 客户端 `localStorage`
- 不引入 JWT，不增加额外依赖
- 新登录生成新 token 替换旧 token（单 session，更安全）

## 数据模型

### users 表

```sql
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,            -- bcrypt hash
    token       TEXT,                     -- 登录 token
    total_games INTEGER DEFAULT 0,
    total_wins  INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);
```

### Player 模型

新增可选的 `user_id: Optional[int]` 字段。匿名玩家 `user_id = None`。

## API

| 方法 | 路径 | 请求体 | 响应 |
|------|------|--------|------|
| POST | `/api/auth/register` | `{username, password}` | `{token, user}` |
| POST | `/api/auth/login` | `{username, password}` | `{token, user}` |
| POST | `/api/auth/logout` | 需 Authorization header | `{ok: true}` |
| GET | `/api/users/me` | 需 Authorization header | `{id, username, total_games, total_wins, total_score, created_at}` |

### 鉴权方式

```
Authorization: Bearer <token>
```

服务端从 `users` 表查 token 对应行，验证通过则注入 `current_user`。

### 错误处理

- 注册：用户名已存在 → 409
- 登录：用户名不存在 / 密码错误 → 401
- 未登录访问需鉴权端点 → 401

## 战绩更新

游戏结束（`ws.py` 收到 `end_game` 或 `detective_correct` → game_over）时：

1. 从 `game_engine.end_game()` 返回的 `standings` 中遍历
2. 对每个 `user_id` 不为空的玩家：`total_games += 1`，`total_score += score`
3. 排名第一的玩家：`total_wins += 1`

## 前端

### 新增文件

- `client/src/views/LoginModal.vue` — 登录/注册弹窗，两个 tab 切换
- `client/src/views/ProfilePanel.vue` — 个人档案面板，展示战绩统计

### 修改文件

- `client/src/stores/room.js` — 新增 `currentUser` 状态，`initAuth()` 从 localStorage 恢复 token 并调用 `/api/users/me`
- `client/src/views/HomeView.vue` — 顶部加"登录/注册"入口，已登录显示用户名和下拉菜单（档案 / 登出）
- `client/src/views/RoomView.vue` — 注册用户自动填充账户昵称，可临时修改

### 数据流

```
登录 → localStorage.set('dolos_user', token)
     → store.initAuth() → GET /api/users/me → currentUser 状态

加入房间 → 如果已登录，携带 user_id
        → Player.user_id 关联账户

游戏结束 → 服务端检查 Player.user_id → 更新 users 表战绩

登录状态 → localStorage 持久化，跨标签页共享
匿名玩家 → sessionStorage 持久化，关标签页消失（不变）
```

## 向后兼容

- 匿名玩法完全不受影响
- 现有 Player token 机制不变
- 现有房间/游戏流程不变
- 现有 API 端点不修改
