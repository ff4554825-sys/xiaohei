# 小黑 (XiaoHei) — Agent OS

状态机驱动的 AI 原生运行时。69 个模块、7 层架构、双模式运行。

## 快速开始

### 安装

```bash
git clone https://github.com/ff4554825-sys/xiaohei.git
cd xiaohei
pip install -e .
```

### 运行

```bash
# CLI 模式
python start.py --mode cli

# Web UI 模式 (浏览器访问 http://localhost:3721)
python start.py --mode web --port 3721

# 双模式
python start.py --mode both
```

首次启动需要配置 DeepSeek API Key:
```bash
# 方式1: 环境变量
export DEEPSEEK_API_KEY="sk-xxx"
python start.py

# 方式2: 配置文件
echo "DEEPSEEK_API_KEY=sk-xxx" > .env
python start.py
```

### Docker

```bash
docker-compose up -d
```

## 架构

```
接入层 (5模块)     — Web UI / CLI / ACP(编辑器) / Gateway(多平台)
控制平面 (11模块)  — FSM引擎 / EventBus / Governance / Policy / Budget / Cron / Contracts
认知层 (11模块)    — TaskParser / Planner / FailureClassifier / Critic / ControlDecider / AgentRuntime
数据平面 (8模块)   — MemoryOS(5层) / MemoryStore(FTS5+TF-IDF) / Ticker / Checkpoint / ContextGatherer
执行平面 (9模块)   — Executor / CapabilityGraph / MCPBus / Sandbox / SkillLibrary / SubAgentPool
校验层 (5模块)     — SyntaxCheck → SemanticCheck → RuntimeCheck → PolicyCheck
可观测层 (6模块)   — Trace / Metrics / Logging / OpenTelemetry / Replay
运行时 (4模块)     — AgentOS(双模式: XiaoHeiFSM + HermesLoop)
```

总模块: **53 个** / 代码行: **~7,000 行**

## API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/chat` | POST | 发送消息 |
| `/api/health` | GET | 健康检查 |
| `/api/config` | GET | 配置查询 |
| `/api/config/key` | POST | 设置 API Key |
| `/ws` | WebSocket | 流式响应 |

## 许可

MIT
