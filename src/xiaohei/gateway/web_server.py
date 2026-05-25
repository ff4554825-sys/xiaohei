"""WebServer — HTTP 服务 + 流式响应 + Web UI (接入层)

功能:
- POST /api/chat  → 流式 SSE 响应
- WebSocket /ws  → 实时推送
- GET /api/memories → 记忆图谱
- GET / → 升级版 Web UI(记忆图谱+设置页+多轮上下文)
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, List
from loguru import logger
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from ..types import Task, TaskType, Event, EventType
from ..control import FSMEngine, EventBus
from ..data import MemoryOS
from ..data.ticker import get_tick_string

# ── 会话管理 ──
_sessions: Dict[str, List[dict]] = {}
_memory = MemoryOS()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


def get_session(sid: str = None) -> str:
    if not sid or sid not in _sessions:
        sid = uuid.uuid4().hex[:8]
        _sessions[sid] = []
    return sid


# ── App ──
def get_sessions():
    return list(_sessions.keys())

app = FastAPI(title="小黑", version="1.0.0")


class WebServer:
    """WebServer 类(兼容旧接口)"""
    def __init__(self, fsm_engine=None, event_bus=None, task_parser=None,
                 planner=None, critic=None, control_decider=None):
        self._fsm = fsm_engine
        self._event_bus = event_bus
    
    def run(self, host="0.0.0.0", port=3721):
        logger.info(f"🚀 小黑 HTTP 服务: http://{host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="warning")


app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "agent": "小黑", "version": "1.0.0"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """聊天 API — 流式 SSE 响应"""
    sid = get_session(req.session_id)
    _sessions[sid].append({"role": "user", "content": req.message, "ts": time.time()})

    async def event_stream():
        yield f"data: {json.dumps({'type': 'tick', 'tick': get_tick_string()})}\n\n"
        yield f"data: {json.dumps({'type': 'session', 'session_id': sid})}\n\n"

        # 模拟流式输出 (实际应接入真正的 streaming LLM)
        words = f"收到: {req.message}\n\n我是小黑, 有什么可以帮你?".split()
        for w in words:
            yield f"data: {json.dumps({'type': 'token', 'text': w + ' '})}\n\n"
            await asyncio.sleep(0.05)

        response_text = " ".join(words)
        _sessions[sid].append({"role": "assistant", "content": response_text, "ts": time.time()})
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/memories")
def get_memories():
    """记忆图谱数据(供前端可视化)"""
    nodes = []
    for entry in _memory.read("", limit=50):
        nodes.append({
            "id": entry.mem_id,
            "label": entry.content[:30],
            "layer": entry.layer,
            "importance": entry.importance,
            "entities": entry.entities,
        })
    return {"nodes": nodes, "edges": []}


@app.get("/api/sessions")
def list_sessions():
    return {"sessions": [{"id": k, "count": len(v)} for k, v in _sessions.items()]}


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    sid = get_session()
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            text = msg.get("message", "")
            _sessions[sid].append({"role": "user", "content": text, "ts": time.time()})
            response = f"收到: {text}"
            await ws.send_json({"type": "token", "text": response})
            _sessions[sid].append({"role": "assistant", "content": response, "ts": time.time()})
    except WebSocketDisconnect:
        pass


# ── Web UI ──
UI_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小黑</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;height:100vh;display:flex;flex-direction:column}
.header{padding:12px 20px;background:#161b22;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:12px}
.header h1{font-size:16px;font-weight:600;flex:1}
.dot{width:8px;height:8px;border-radius:50%;background:#3fb950;display:inline-block}
.btn{background:#21262d;border:1px solid #30363d;color:#c9d1d9;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px}
.btn:hover{background:#30363d}
.chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
.msg{padding:12px 16px;border-radius:12px;max-width:80%;line-height:1.6;font-size:14px}
.user{background:#1f6feb;align-self:flex-end;border-bottom-right-radius:4px}
.assistant{background:#21262d;align-self:flex-start;border:1px solid #30363d;border-bottom-left-radius:4px}
.inp{padding:16px 20px;background:#161b22;border-top:1px solid #30363d;display:flex;gap:12px}
.inp input{flex:1;padding:10px 16px;border-radius:8px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;font-size:14px;outline:none}
.inp input:focus{border-color:#1f6feb}
.inp button{padding:10px 24px;border-radius:8px;border:none;background:#1f6feb;color:#fff;font-size:14px;cursor:pointer}
.inp button:hover{background:#388bfd}.inp button:disabled{opacity:0.5;cursor:not-allowed}
.panel{position:fixed;right:0;top:0;width:320px;height:100%;background:#161b22;border-left:1px solid #30363d;transform:translateX(100%);transition:transform 0.3s;overflow-y:auto;z-index:100}
.panel.open{transform:translateX(0)}
.panel h3{padding:16px;font-size:14px;color:#8b949e;border-bottom:1px solid #30363d}
.mem-item{padding:10px 16px;margin:4px 8px;background:#21262d;border-radius:6px;font-size:12px;border-left:3px solid #58a6ff}
.setting-item{padding:12px 16px;display:flex;justify-content:space-between;align-items:center;font-size:13px}
.setting-item input{width:200px;padding:6px 10px;border-radius:4px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9}
.tabs{display:flex;border-bottom:1px solid #30363d}
.tab{flex:1;padding:10px;text-align:center;cursor:pointer;font-size:13px;color:#8b949e}
.tab.active{color:#c9d1d9;border-bottom:2px solid #1f6feb}
.typing{color:#8b949e;font-size:12px;padding:4px 16px}
</style>
</head>
<body>
<div class="header">
<span class="dot" id="status-dot"></span>
<h1 id="agent-name">小黑</h1>
<button class="btn" onclick="togglePanel('memories')">记忆</button>
<button class="btn" onclick="togglePanel('settings')">设置</button>
</div>
<div class="chat" id="chat"></div>
<div class="inp">
<input id="inp" placeholder="发消息给小黑..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}" autofocus>
<button id="send-btn" onclick="send()">发送</button>
</div>

<div class="panel" id="panel">
<div class="tabs">
<div class="tab active" id="tab-memories" onclick="switchTab('memories')">记忆图谱</div>
<div class="tab" id="tab-settings" onclick="switchTab('settings')">设置</div>
</div>
<div id="panel-memories"></div>
<div id="panel-settings" style="display:none">
<div class="setting-item"><span>模型</span><select id="sel-model" style="padding:6px;border-radius:4px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9"><option>deepseek-chat</option></select></div>
<div class="setting-item"><span>温度</span><input id="inp-temp" type="range" min="0" max="2" step="0.1" value="0.7"></div>
<div class="setting-item"><span>最大Token</span><input id="inp-tokens" type="number" value="4096" style="width:80px"></div>
<div class="setting-item"><button class="btn" style="width:100%;margin-top:8px" onclick="clearHistory()">清除对话历史</button></div>
</div>
</div>

<script>
let sessionId = null, loading = false;

async function send() {
const inp = document.getElementById('inp');
const btn = document.getElementById('send-btn');
const msg = inp.value.trim(); if(!msg||loading) return;
inp.value=''; loading=true; btn.disabled=true;
addMsg(msg,'user');
const chat=document.getElementById('chat');
const typing=document.createElement('div');typing.className='typing';typing.id='typing';typing.textContent='小黑正在思考...';chat.appendChild(typing);chat.scrollTop=chat.scrollHeight;
try{
const resp=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,session_id:sessionId})});
const reader=resp.body.getReader();const decoder=new TextDecoder();let buf='';
typing.remove();const msgDiv=document.createElement('div');msgDiv.className='msg assistant';chat.appendChild(msgDiv);
while(true){const{done,value}=await reader.read();if(done)break;buf+=decoder.decode(value,{stream:true});
const lines=buf.split('\n');buf=lines.pop()||'';
for(const line of lines){if(!line.startsWith('data: '))continue;
try{const d=JSON.parse(line.slice(6));
if(d.type==='session')sessionId=d.session_id;
else if(d.type==='token')msgDiv.textContent+=d.text;
else if(d.type==='tick')document.getElementById('status-dot').style.background='#3fb950';
else if(d.type==='done'){chat.scrollTop=chat.scrollHeight}}catch(e){}}}}
catch(e){typing.remove();addMsg('请求失败: '+e.message,'assistant')}
finally{loading=false;btn.disabled=false;chat.scrollTop=chat.scrollHeight}}

function addMsg(t,r){const c=document.getElementById('chat');const d=document.createElement('div');d.className='msg '+r;d.textContent=t;c.appendChild(d);c.scrollTop=c.scrollHeight}
function togglePanel(t){const p=document.getElementById('panel');p.classList.toggle('open');if(p.classList.contains('open'))switchTab(t||'memories')}
function switchTab(t){document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');
document.getElementById('panel-memories').style.display=t==='memories'?'block':'none';
document.getElementById('panel-settings').style.display=t==='settings'?'block':'none';
if(t==='memories')loadMemories()}
async function loadMemories(){const d=document.getElementById('panel-memories');
try{const r=await fetch('/api/memories');const j=await r.json();d.innerHTML=j.nodes.map(n=>'<div class="mem-item">'+n.label+'<br><small>'+n.layer+' · 重要度:'+n.importance+'</small></div>').join('')||'<div style="padding:16px;color:#8b949e">暂无记忆</div>'}catch(e){d.innerHTML='加载失败'}}
function clearHistory(){if(confirm('确认清除?')){document.getElementById('chat').innerHTML='';addMsg('对话历史已清除','assistant')}}
addMsg('你好, 我是小黑。有什么可以帮你?','assistant');
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(UI_HTML)


def run(host="0.0.0.0", port=3721):
    logger.info(f"🚀 小黑 HTTP 服务: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
