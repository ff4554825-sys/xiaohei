"""Tool Intelligence — 真实工具智能层

核心能力:
1. 调用 LLM 做语义工具匹配(不是关键词)
2. 调用 LLM 做工具组合规划(不是if/else)
3. 调用 LLM 做调用前风险评估(不是关键词黑名单)
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger
from ..cognition.llm import call_llm, call_llm_json


TOOL_REGISTRY = {
    "python_exec": {
        "name": "执行Python代码",
        "description": "执行Python代码并返回结果, 适合作图, 分析, 计算等",
        "scenarios": ["计算", "绘图", "数据分析", "写脚本", "执行代码"],
        "risk": "low",
    },
    "web_search": {
        "name": "联网搜索",
        "description": "搜索互联网信息, 获取最新的知识",
        "scenarios": ["搜索", "查询", "查资料", "找信息", "了解"],
        "risk": "low",
    },
    "file_read": {
        "name": "读取文件",
        "description": "读取本地文件的内容",
        "scenarios": ["读文件", "打开文件", "查看文件"],
        "risk": "low",
    },
    "file_write": {
        "name": "写入文件",
        "description": "将内容写入本地文件",
        "scenarios": ["写文件", "保存", "创建文件"],
        "risk": "medium",
    },
    "memory_search": {
        "name": "搜索记忆",
        "description": "在历史记忆中搜索相关信息",
        "scenarios": ["之前", "历史", "记得", "回忆", "记忆"],
        "risk": "low",
    },
    "desktop_open": {
        "name": "打开应用程序",
        "description": "通过Win菜单搜索并打开应用程序(记事本/浏览器/计算器...)",
        "scenarios": ["打开", "启动", "运行"],
        "risk": "low",
    },
    "desktop_type": {
        "name": "键盘输入",
        "description": "在键盘上输入文本内容",
        "scenarios": ["输入", "键入", "打字"],
        "risk": "low",
    },
    "desktop_click": {
        "name": "桌面点击",
        "description": "点击桌面上指定坐标位置",
        "scenarios": ["点击", "双击", "右键"],
        "risk": "medium",
    },
    "desktop_screenshot": {
        "name": "截图",
        "description": "截取当前屏幕画面",
        "scenarios": ["截图", "截屏", "屏幕"],
        "risk": "low",
    },
    "desktop_hotkey": {
        "name": "快捷键",
        "description": "执行键盘快捷键(alt+tab, ctrl+c, win+r...)",
        "scenarios": ["切换", "快捷键", "组合键"],
        "risk": "low",
    },
}


class ToolIntelligence:
    """工具智能层 — 全部用 LLM 决策"""
    
    def semantic_search(self, task: str, top_k: int = 3) -> List[dict]:
        """真实语义搜索: 用 LLM 匹配工具"""
        tools_desc = "\n".join([
            f"- {k}: {v['description']} (适用场景: {', '.join(v['scenarios'])})"
            for k, v in TOOL_REGISTRY.items()
        ])
        
        result = call_llm_json(
            "你是一个工具匹配专家。根据用户任务找出最合适的3个工具, 返回JSON数组。",
            f"用户任务: {task}\n\n可用工具:\n{tools_desc}\n\n返回格式: [{{\"tool\": \"工具名\", \"reason\": \"匹配理由\", \"confidence\": 0-1}}]"
        )
        
        if isinstance(result, dict) and "error" not in result:
            return [result] if isinstance(result.get(0), dict) else list(result.values()) if isinstance(result, dict) else []
        
        # 降级: 基于场景关键词
        results = []
        task_lower = task.lower()
        for name, info in TOOL_REGISTRY.items():
            score = 0
            for s in info["scenarios"]:
                if s in task_lower:
                    score += 0.25
            if score > 0:
                results.append({"tool": name, "reason": info["description"], "confidence": score})
        
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:top_k]
    
    def plan(self, task: str, available_tools: List[str] = None) -> dict:
        """真实多工具规划: 用 LLM 规划工具链"""
        tools_desc = "\n".join([
            f"- {k}: {v['description']}"
            for k, v in TOOL_REGISTRY.items()
            if not available_tools or k in available_tools
        ])
        
        result = call_llm_json(
            "你是一个工具规划专家。根据用户任务规划工具链, 返回JSON。",
            f"任务: {task}\n\n可用工具:\n{tools_desc}\n\n返回格式: {json.dumps({'goal':'任务目标','chain':['工具1','工具2',...],'reasoning':'规划理由','estimated_steps':3})}"
        )
        
        if isinstance(result, dict) and "chain" in result:
            return result
        
        return {"goal": task, "chain": ["llm_chat"], "reasoning": "通用响应", "estimated_steps": 1}
    
    def critic(self, tool: str, task: str) -> dict:
        """真实调用前评估: 用 LLM 判断风险"""
        info = TOOL_REGISTRY.get(tool, {})
        
        result = call_llm_json(
            "你是一个安全审查专家。评估工具调用是否安全合理, 返回JSON。",
            f"工具: {tool} ({info.get('description', '?')})\n任务: {task}\n\n返回格式: {json.dumps({'allowed': True,'risk_level':'low','warnings':[],'reason':'允许执行'})}"
        )
        
        if isinstance(result, dict) and "allowed" in result:
            return result
        
        return {"allowed": True, "risk_level": info.get("risk", "low"), "warnings": [], "reason": "风险评估不可用, 默认放行"}
