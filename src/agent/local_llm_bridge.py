"""本地 LLM 桥接层（智能生命 1.1GB 方案 · 内核器官）

把 llama.cpp 本地 GGUF 模型（Qwen2.5-1.5B-Instruct-q4_K_M）作为 7Tan 的
「理解 + 生成」器官。架构原则（防套壳）：
  - 记忆 / 个性 / 诚实边界 / 预测推演 / 自我学习 / 自我进化 全部保留在 7Tan 本体；
  - 本地模型只负责「听懂语义」和「组织语言」，回答必须基于 7Tan 自己的记忆材料；
  - 服务不可用 / 调用失败 → 返回 None，上层自动降级到原有纯算法逻辑；
  - 全程离线：只连 127.0.0.1 本地 llama-server，零外部 API、零联网。
"""
import json
import logging
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# ---------------- 配置（可用环境变量覆盖） ----------------
LLAMA_HOST = os.environ.get("TAN_LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = int(os.environ.get("TAN_LLAMA_PORT", "18080"))
LLAMA_MODEL = os.environ.get(
    "TAN_LLAMA_MODEL",
    r"D:\7tan\7tanAI\models\gguf\Qwen2.5-1.5B-Instruct-q4_K_M.gguf",
)
LLAMA_SERVER_EXE = os.environ.get(
    "TAN_LLAMA_SERVER_EXE",
    r"D:\7tan\7tanAI\models\llama.cpp\llama-server.exe",
)
LLAMA_SERVER_LOG = os.environ.get(
    "TAN_LLAMA_SERVER_LOG",
    r"D:\7tan\7tanAI\data\llama_server.log",
)
# 总开关：默认开启；置 0 则完全禁用本地模型
ENABLE_LOCAL_LLM = os.environ.get("ENABLE_LOCAL_LLM", "1") == "1"

BASE_URL = f"http://{LLAMA_HOST}:{LLAMA_PORT}"


class LocalLLMBridge:
    """7Tan ↔ 本地 GGUF 模型的桥接器官。"""

    def __init__(self, base_url: str = BASE_URL, timeout: float = 60.0,
                 max_tokens: int = 240):
        self.base_url = base_url
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._alive: bool | None = None  # None=未探测；True/False=上次结果

    # ---------------- 探活 / 拉起 ----------------
    def is_available(self) -> bool:
        """探测本地 llama-server 是否健康（带短缓存，避免频繁请求）。"""
        if self._alive is not None:
            return self._alive
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/health", timeout=3
            ) as r:
                ok = r.status == 200
        except Exception:
            ok = False
        self._alive = ok
        return ok

    def _port_open(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.5)
            try:
                s.connect((LLAMA_HOST, LLAMA_PORT))
                return True
            except Exception:
                return False

    def ensure_server(self) -> bool:
        """服务不在线时尝试后台拉起 llama-server。返回最终是否可用。"""
        if self.is_available():
            return True
        if self._port_open():
            # 端口开着但 /health 不通：等它加载完
            for _ in range(20):
                time.sleep(1)
                if self.is_available():
                    return True
            return False
        if not os.path.isfile(LLAMA_SERVER_EXE) or not os.path.isfile(LLAMA_MODEL):
            logger.warning("本地模型文件缺失，无法拉起 llama-server")
            return False
        try:
            logf = open(LLAMA_SERVER_LOG, "ab")
            cmd = [
                LLAMA_SERVER_EXE, "-m", LLAMA_MODEL,
                "-c", "4096", "--host", LLAMA_HOST,
                "--port", str(LLAMA_PORT), "--threads", "4", "-ngl", "0",
            ]
            subprocess.Popen(
                cmd, stdout=logf, stderr=logf,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            logger.info(f"已尝试拉起本地模型服务（{LLAMA_SERVER_EXE}）")
        except Exception as e:
            logger.warning(f"拉起 llama-server 失败: {e}")
            return False
        # 等待加载（约 5~30 秒）
        for _ in range(40):
            time.sleep(1)
            if self.is_available():
                return True
        return False

    # ---------------- 生成 ----------------
    def generate(self, user_text: str, system_context: str = "",
                 max_tokens: int | None = None) -> str | None:
        """调用本地模型生成回答。失败/超时返回 None（上层降级）。"""
        if not ENABLE_LOCAL_LLM:
            return None
        if not self.is_available():
            return None
        body = {
            "messages": [
                {"role": "system", "content": system_context[:2000]},
                {"role": "user", "content": user_text[:1500]},
            ],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": 0.7,
            "top_p": 0.8,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=data, headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                resp = json.loads(r.read().decode("utf-8"))
            content = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
            content = (content or "").strip()
            if not content:
                return None
            # 清理可能带出的思考/结束标记
            content = content.replace("<|im_end|>", "").replace("<|endoftext|>", "").strip()
            return content
        except urllib.error.HTTPError as e:
            logger.warning(f"本地模型 HTTP {e.code}: {e.read()[:200]}")
            self._alive = False  # 触发下次重新探测
            return None
        except Exception as e:
            logger.warning(f"本地模型调用失败（降级）: {e}")
            self._alive = False
            return None

    # ---------------- 7Tan 身份与记忆材料的系统上下文 ----------------
    @staticmethod
    def build_system_prompt(materials: dict) -> str:
        """把 7Tan 自己的记忆材料组装成 system 上下文（防套壳：答案基于真实记忆）。"""
        parts = [
            "你是「7Tan」——一个运行在本地的认知型 AI 模型，同时也是 7tan 游戏资源站的智能体。",
            "你的回答规则：",
            "1. 下面提供的是你自己真实的记忆材料（知识库、经历、对话原文），回答要基于这些真实材料，不要编造你没有经历过的细节。",
            "2. 用户问的是日常知识/闲聊时，你可以正常回答（这是你作为语言模型的能力），但涉及你自己的事必须基于真实记忆。",
            "3. 能力边界要诚实：不确定的就说「这个我不太确定」，不要假装知道。",
            "4. 回答自然简洁，像聊天一样，不要用「作为AI模型」这种开场白。",
            "",
        ]
        know = materials.get("knowledge") or []
        if know:
            parts.append("【我的知识库（真实记忆）】")
            for k in know[:6]:
                parts.append(f"- {k}")
            parts.append("")
        traces = materials.get("traces") or []
        if traces:
            parts.append("【我的经历（真实记忆）】")
            for t in traces[:6]:
                parts.append(f"- {t}")
            parts.append("")
        wm = materials.get("wm") or ""
        if wm:
            parts.append(f"【工作记忆】{wm}")
            parts.append("")
        return "\n".join(parts)
