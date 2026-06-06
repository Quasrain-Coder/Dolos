# Dolos — 瞎掰王

多人实时派对游戏。一法官出题，其他人编假定义，全员投票猜真相。

## 技术栈

- 后端：Python FastAPI + WebSocket + SQLite
- 前端：Vue 3 + Vite + Pinia

## 快速开始

### 后端

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000
```

### 前端

```bash
cd client
npm install
npm run dev
```

打开 http://localhost:5173 即可游玩。

## 外网分享

```bash
cloudflared tunnel --url http://localhost:8000
```

获得公网 URL，发给朋友即可。

## 运行测试

```bash
cd server && source .venv/bin/activate && python -m pytest tests/ -v
```

## 规则

- 至少 4 人开局
- 法官抽题 → 玩家编假答案 → 全员投票 → 揭晓得分
- 猜对 +2 分，骗到别人 +1 分/人，法官无人猜中 +3 分
