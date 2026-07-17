"""
实时代码补全 API 服务。
启动本地 HTTP 服务器，供 VS Code 扩展调用，实现 AI 代码补全。
"""
import json
import os
import sys
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# 服务状态
_server = None
_server_thread = None
PORT = 17890  # 7Tan 代码补全专用端口


class CompletionHandler(BaseHTTPRequestHandler):
    """处理来自 VS Code 扩展的补全请求"""
    
    def log_message(self, format, *args):
        pass  # 静默日志
    
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_POST(self):
        if self.path == "/api/complete":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                
                prefix = data.get("prefix", "")
                suffix = data.get("suffix", "")
                language = data.get("language", "python")
                file_path = data.get("file_path", "")
                
                prompt = f"""你是代码补全助手。根据上下文补全代码。

语言: {language}
文件: {file_path}

上文:
```{language}
{prefix[-2000:]}
```

下文:
```{language}
{suffix[:500]}
```

请直接输出补全的代码片段（只补全缺失部分，不要重复已有代码），控制在 1-10 行内:"""
                
                self._send_json({
                    "success": True,
                    "prompt": prompt,
                    "prefix": prefix[-2000:],
                    "suffix": suffix[:500],
                    "language": language
                })
                
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
        else:
            self._send_json({"error": "Not Found"}, 404)
    
    def do_GET(self):
        if self.path == "/api/health":
            self._send_json({"status": "ok", "service": "7Tan Code Completion"})
        elif self.path == "/api/status":
            self._send_json({
                "status": "running",
                "port": PORT,
                "vs_code_extension": "需要安装 7Tan Copilot 扩展"
            })
        else:
            self._send_json({"error": "Not Found"}, 404)


@register_tool(
    name="completion_start",
    description="启动本地 AI 代码补全 HTTP 服务（端口 17890），供 VS Code 扩展调用。",
    parameters={},
    category="dev"
)
def completion_start() -> str:
    """启动代码补全 HTTP 服务（端口 17890）。
    启动后 VS Code 扩展可连接此服务获取 AI 补全。
    """
    global _server, _server_thread
    
    if _server is not None:
        return f"⚠️ 代码补全服务已在运行中 (端口 {PORT})"
    
    try:
        _server = HTTPServer(("127.0.0.1", PORT), CompletionHandler)
        _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
        _server_thread.start()
        return f"""✅ 代码补全服务已启动!
  地址: http://127.0.0.1:{PORT}
  健康检查: http://127.0.0.1:{PORT}/api/health
  状态: http://127.0.0.1:{PORT}/api/status
  
  📌 下一步: 在 VS Code 中安装 7Tan Copilot 扩展
  （扩展源码在 D:\\7tan\\7tanAI\\extensions\\vscode-7tan-copilot\\）"""
    except Exception as e:
        return f"❌ 启动失败: {e}"


@register_tool(
    name="completion_stop",
    description="停止代码补全 HTTP 服务。",
    parameters={},
    category="dev"
)
def completion_stop() -> str:
    """停止代码补全 HTTP 服务。"""
    global _server, _server_thread
    
    if _server is None:
        return "⚠️ 代码补全服务未运行。"
    
    try:
        _server.shutdown()
        _server = None
        _server_thread = None
        return "✅ 代码补全服务已停止。"
    except Exception as e:
        return f"❌ 停止失败: {e}"


@register_tool(
    name="completion_status",
    description="查看代码补全服务运行状态。",
    parameters={},
    category="dev"
)
def completion_status() -> str:
    """查看代码补全服务状态。"""
    global _server
    if _server is not None:
        return f"✅ 运行中 — http://127.0.0.1:{PORT}/api/health"
    return "⏸️ 未启动 — 使用 completion_start 启动服务"
