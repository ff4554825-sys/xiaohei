"""ErrMsg — 用户友好的错误提示 (接入层)

将内部异常翻译为中文用户提示。
"""

USER_FRIENDLY = {
    "SyntaxError": "代码语法有误, 检查后再试",
    "ImportError": "找不到需要的模块, 试试 pip install",
    "ConnectionError": "网络连接失败, 检查代理或网络",
    "TimeoutError": "请求超时, 可能网络较慢, 稍后再试",
    "PermissionError": "没有权限执行该操作",
    "FileNotFoundError": "找不到文件, 检查路径是否正确",
    "KeyError": "缺少配置项, 检查 config.yaml",
    "ValueError": "参数值不正确, 检查输入",
    "TypeError": "数据类型不匹配",
    "IndexError": "索引超出范围",
    "AttributeError": "对象没有该属性, 可能是版本不匹配",
    "ModuleNotFoundError": "缺少依赖, 运行 pip install 安装",
    "json.JSONDecodeError": "数据格式错误, 请检查输入",
    "httpx.ConnectError": "无法连接服务器, 检查网络",
    "httpx.TimeoutException": "请求超时, 稍后再试",
    "openai.APIError": "AI 模型调用失败, 检查 API Key",
    "openai.RateLimitError": "请求过于频繁, 稍后再试",
    "openai.AuthenticationError": "API Key 无效, 检查配置",
}


def friendly_error(error: Exception) -> str:
    """将异常转换为友好中文提示"""
    error_name = type(error).__name__
    
    # 尝试精确匹配
    for pattern, msg in USER_FRIENDLY.items():
        if pattern in error_name or pattern in str(error):
            return f"❌ {msg}"
    
    # 已知错误信息中的关键词
    error_str = str(error).lower()
    if "api key" in error_str:
        return "❌ API Key 未配置或无效, 请在设置中输入"
    if "timeout" in error_str:
        return "⏱ 请求超时, 请稍后再试"
    if "connection" in error_str:
        return "🌐 网络连接失败, 请检查网络设置"
    if "not found" in error_str:
        return "🔍 找不到资源, 请检查路径"
    if "permission" in error_str:
        return "🔒 没有权限执行该操作"
    if "quota" in error_str or "rate" in error_str:
        return "⏳ 请求频率超限, 请稍后再试"
    if "memory" in error_str:
        return "💾 内存不足, 请重启应用"
    
    return f"⚠️ 出错了: {str(error)[:100]}"
