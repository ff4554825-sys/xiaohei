# 小黑 (XiaoHei) Agent OS

状态机驱动的 AI 原生运行时。

## 核心特性

- **FSM 引擎** — 13 个状态 + 迁移矩阵 + 非法跳转拦截
- **双模式运行** — 小黑模式(FSM驱动) + Hermes模式(循环驱动)
- **7层架构** — 接入/控制/认知/数据/执行/校验/可观测
- **失败分类** — 7类失败 × 8种恢复策略
- **降级链** — 6类降级优先级 + 熔断器
- **技能库** — 二级缓存(Level 0检索 + Level 1注入)
- **记忆系统** — 5层 MemoryOS + 实体图 + 后台整合

## 快速开始

```bash
# 安装
git clone https://github.com/ff4554825-sys/xiaohei.git
cd xiaohei
pip install -e .

# 运行
export DEEPSEEK_API_KEY="sk-xxx"
python start.py --mode web

# 打开浏览器
# http://localhost:3721
```

## 架构

```
接入层 → 控制平面 → 认知层 → 数据平面 → 执行平面 → 校验层 → 可观测层
```
