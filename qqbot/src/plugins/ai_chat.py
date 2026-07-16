"""
AI 聊天插件 - 接入 DeepSeek，支持上下文对话
API Key 自动从系统环境变量读取
"""

from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot, Event
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
import httpx
import json
import os
from collections import defaultdict

# API 配置 - 直接从环境变量读取（7tan-editor 已设置）
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

# 每个群/用户的对话历史（最多保留10轮）
history: dict = defaultdict(list)
MAX_HISTORY = 10


# === 显式 /chat 命令 ===
chat_cmd = on_command("chat", aliases={"聊天", "问", "ask"}, priority=10)

@chat_cmd.handle()
async def handle_chat(matcher: Matcher, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    if not text:
        await matcher.finish("请输入你想说的话，例如: /chat 今天天气怎么样？")

    reply = await ai_chat("user_console", text)
    await matcher.finish(reply)


# === @机器人 自动聊天 ===
auto_chat = on_message(rule=to_me(), priority=99)

@auto_chat.handle()
async def handle_auto_chat(event: Event):
    text = str(event.get_message()).strip()
    if not text:
        await auto_chat.finish("我在呢～有什么可以帮你的？😊")

    user_id = str(event.get_user_id())
    reply = await ai_chat(user_id, text)
    await auto_chat.finish(reply)


# === AI 调用核心 ===
async def ai_chat(session_id: str, message: str) -> str:
    """调用 DeepSeek API 获取回复"""
    if not API_KEY:
        return "⚠️ AI功能未配置，请设置环境变量 DEEPSEEK_API_KEY"

    # 构建对话历史
    messages = history.get(session_id, [])[-MAX_HISTORY * 2:]
    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "你是七坛机器人，一个热心的AI助手。回答简洁友好，用中文。"},
                        *messages,
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]

            # 保存历史
            history[session_id].append({"role": "user", "content": message})
            history[session_id].append({"role": "assistant", "content": reply})
            if len(history[session_id]) > MAX_HISTORY * 2:
                history[session_id] = history[session_id][-MAX_HISTORY * 2:]

            return reply

    except httpx.HTTPError as e:
        return f"⚠️ AI服务连接失败: {e}"
    except Exception as e:
        return f"⚠️ 出错了: {e}"
