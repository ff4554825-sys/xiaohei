"""Tool Intelligence Layer — 工具智能层

核心升级:
1. Tool Semantic Search — 语义搜索匹配工具
2. Multi-Tool Planner — 智能规划工具组合
3. Tool Critic — 调用前评估(这个工具现在用合理吗)
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ToolDef:
    """工具定义"""
    name: str
    description: str
    category: str = "general"     # general / desktop / code / web / data
    parameters: dict = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    
    def to_lightweight(self) -> dict:
        return {"name": self.name, "description": self.description[:60], "category": self.category}


@dataclass
class ToolPlan:
    """工具使用计划"""
    goal: str
    chain: List[str]          # 工具名链: ["screen_capture", "ocr_detect", "click"]
    alternatives: List[List[str]] = field(default_factory=list)
    estimated_steps: int = 0
    confidence: float = 0.0


# ── 默认工具注册表 ──
DEFAULT_TOOLS = [
    ToolDef("python_exec", "执行Python代码", "code",
            examples=["计算1+1", "读取文件内容"]),
    ToolDef("web_search", "搜索网络信息", "web",
            examples=["搜索最近的新闻"]),
    ToolDef("screen_capture", "截取桌面屏幕", "desktop",
            examples=["截图当前屏幕"]),
    ToolDef("element_detect", "检测屏幕中的按钮/文字位置", "desktop",
            examples=["找到发送按钮的位置"]),
    ToolDef("mouse_click", "点击屏幕上的坐标", "desktop",
            examples=["点击(100,200)位置"]),
    ToolDef("keyboard_type", "在键盘上输入文本", "desktop",
            examples=["输入'hello world'"]),
    ToolDef("file_read", "读取文件内容", "data",
            examples=["打开config.yaml"]),
    ToolDef("file_write", "写入文件", "data",
            examples=["保存结果到output.txt"]),
    ToolDef("memory_search", "搜索历史记忆", "data",
            examples=["之前讨论过什么"]),
    ToolDef("skill_load", "加载已保存的技能", "general",
            examples=["加载文件监控技能"]),
    ToolDef("capability_route", "按能力图谱路由任务", "general",),
    ToolDef("mcp_call", "通过MCP调用远程工具", "general",),
    ToolDef("llm_chat", "直接对话LLM", "general",),
]


class ToolRegistry:
    """工具注册表(智能版)"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        for t in DEFAULT_TOOLS:
            self._tools[t.name] = t
    
    def register(self, tool: ToolDef):
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)
    
    def all(self) -> List[ToolDef]:
        return list(self._tools.values())


class ToolSemanticSearch:
    """工具语义搜索 — 根据任务描述匹配最佳工具"""
    
    def __init__(self, registry: ToolRegistry):
        self._registry = registry
    
    def search(self, task: str, top_k: int = 3) -> List[Tuple[ToolDef, float]]:
        """搜索匹配的工具(基于关键词)"""
        task_lower = task.lower()
        scored = []
        
        for tool in self._registry.all():
            score = 0.0
            
            # 工具名匹配
            if tool.name.lower() in task_lower:
                score += 0.6
            for kw in tool.name.lower().split("_"):
                if kw in task_lower:
                    score += 0.2
            
            # 描述匹配
            desc_words = set(tool.description.lower().split())
            task_words = set(task_lower.split())
            overlap = len(desc_words & task_words)
            if overlap > 0:
                score += overlap * 0.1
            
            # 示例匹配
            for ex in tool.examples:
                if any(w in task_lower for w in ex.lower().split()):
                    score += 0.15
            
            if score > 0:
                scored.append((tool, round(min(score, 1.0), 2)))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class MultiToolPlanner:
    """多工具规划器 — 组合工具链完成任务"""
    
    # 预定义工具链
    CHAINS = {
        "desktop_click": ["screen_capture", "element_detect", "mouse_click"],
        "desktop_type": ["screen_capture", "element_detect", "mouse_click", "keyboard_type"],
        "web_research": ["web_search", "web_search", "memory_search"],
        "code_task": ["python_exec", "file_write"],
        "file_operation": ["file_read", "python_exec", "file_write"],
    }
    
    def plan(self, task: str, available_tools: List[str] = None) -> ToolPlan:
        """规划工具链"""
        task_lower = task.lower()
        
        # 匹配预定义链
        if "点击" in task_lower or "click" in task_lower:
            chain = self.CHAINS["desktop_click"]
        elif "输入" in task_lower or "打字" in task_lower or "type" in task_lower:
            chain = self.CHAINS["desktop_type"]
        elif "搜索" in task_lower or "查" in task_lower:
            chain = self.CHAINS["web_research"]
        elif "执行" in task_lower or "运行" in task_lower or "计算" in task_lower:
            chain = self.CHAINS["code_task"]
        else:
            chain = ["python_exec"]
        
        # 过滤掉不可用的工具
        if available_tools:
            chain = [t for t in chain if t in available_tools]
        
        return ToolPlan(
            goal=task,
            chain=chain,
            alternatives=[["python_exec"]],
            estimated_steps=len(chain),
            confidence=0.7 if chain else 0.3,
        )


class ToolCritic:
    """工具批评 — 调用前评估合理性"""
    
    def evaluate(self, tool: str, task: str, context: dict = None) -> Dict[str, Any]:
        """评估工具调用是否合理"""
        warnings = []
        
        # 安全检查
        if tool == "mouse_click":
            if "删除" in task.lower() or "format" in task.lower():
                warnings.append("⚠️ 高危操作: 可能触发删除/格式化")
            if "确认" in task.lower() or "确定" in task.lower():
                warnings.append("🛡️ 需要确认对话框, 请先确认用户意图")
        
        if tool == "keyboard_type":
            if "密码" in task.lower() or "password" in task.lower():
                warnings.append("🔒 检测到密码输入, 确认用户授权")
        
        if tool == "python_exec":
            if "rm -rf" in task or "format" in task:
                warnings.append("🚫 高危命令, 已拦截")
                return {"allowed": False, "warnings": warnings, "reason": "高危操作拦截"}
        
        return {
            "allowed": len([w for w in warnings if "🚫" in w]) == 0,
            "warnings": warnings,
            "confidence": max(0.3, 1.0 - len(warnings) * 0.2),
        }
