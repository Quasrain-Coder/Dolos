# Dolos — 瞎掰王

多人实时派对游戏。隐藏角色推理：老实人说真话，大聪明来破案。

**玩法：** 大聪明从 3 道备选题中选题 → 全员编答案 → 大聪明投票猜真 → 揭晓得分

完整规则见 [游戏说明](docs/游戏说明.md)。

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

## 规则概要

- 至少 2 人开局（推荐 4-8 人）
- 系统随机分配老实人/大聪明/瞎掰人
- 大聪明从 3 道备选题中选题 → 全员编答案 → 大聪明投票+猜人
- 投中真答案 +2 分，骗到别人 +1 分/人，大聪明猜中老实人 +3 分
