# 架构

## 整体层级

```
接入层 (5模块)     Web UI / CLI / ACP / Gateway / 守护
控制平面 (12模块)  FSM / EventBus / Governance / Policy / Budget / Contracts / Lifecycle / Credentials
认知层 (11模块)    TaskParser / Planner / FailureClassifier / Critic / ControlDecider / AgentRuntime
数据平面 (9模块)   MemoryOS(5层) / MemoryStore / Ticker / ContextGatherer / CheckpointOS / Compressor
执行平面 (9模块)   Executor / CapabilityGraph / MCPBus / Sandbox / SkillLibrary / SkillSystem
校验层 (5模块)     SyntaxCheck → SemanticCheck → RuntimeCheck → PolicyCheck
可观测层 (6模块)   Trace / Metrics / Logging / OpenTelemetry / Replay
运行时 (4模块)     AgentOS (双模式)
```

## 状态机

```
AgentPhase(13个状态):
  IDLE → PARSE_TASK → DIVERGE → SEARCH → SCORER → DECOMPOSE
  → EXECUTE → VERIFY → CRITIC
  → REFLECT / RETRY / FINISH / ERROR / HANDOFF

迁移矩阵硬编码在 control/fsm.py
非法跳转由 validate_transition() 拦截
```

## 核心数据流

```
用户输入 → TaskParser → Planner(多方案+打分) → Executor
  → Verify(4层校验) → Critic(自评)
  → ControlDecider(决定性路由)
    ├─ retry → 重试
    ├─ reflect → 反思修正
    ├─ fallback → 降级
    ├─ finish → 完成
    └─ handoff → 人工接管
```
