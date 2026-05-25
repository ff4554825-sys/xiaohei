# API 参考

## HTTP API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/chat` | POST | 发送消息给 Agent |
| `/api/health` | GET | 健康检查 |
| `/api/config` | GET | 配置查询 |
| `/api/config/key` | POST | 设置 API Key |
| `/api/memory` | GET | 记忆查询 |
| `/api/hotspots` | GET | 记忆图谱数据 |
| `/ws` | WebSocket | 流式响应 |

### POST /api/chat

```json
{
  "message": "你好",
  "session_id": null
}
```

### GET /api/health

```json
{"status":"ok","agent":"XiaoHei","version":"1.0.0"}
```

## CLI

```bash
python start.py --mode cli
```

## ACP (编辑器集成)

```bash
python -m src.xiaohei.gateway.acp
```
