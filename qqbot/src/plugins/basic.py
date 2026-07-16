"""
基础命令插件 - 打招呼、帮助、状态
"""

from nonebot import on_command, on_keyword
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot, Event
from nonebot.params import CommandArg
import time
import platform


# === 问候 ===
hello = on_command("hello", aliases={"你好", "hi", "在吗"}, rule=to_me(), priority=10)

@hello.handle()
async def handle_hello():
    hour = time.localtime().tm_hour
    if hour < 6:
        greeting = "凌晨好 🌙"
    elif hour < 9:
        greeting = "早上好 ☀️"
    elif hour < 12:
        greeting = "上午好 🌤️"
    elif hour < 14:
        greeting = "中午好 ☀️"
    elif hour < 18:
        greeting = "下午好 🌈"
    elif hour < 22:
        greeting = "晚上好 🌙"
    else:
        greeting = "夜深了 🌙"

    await hello.finish(
        f"{greeting}！我是七坛机器人 🤖\n"
        f"发送 /help 查看我能做什么\n"
        f"发送 /状态 查看系统状态"
    )


# === 帮助 ===
help_cmd = on_command("help", aliases={"帮助", "菜单", "功能"}, priority=10)

@help_cmd.handle()
async def handle_help():
    msg = (
        "📋 **七坛机器人 功能菜单**\n\n"
        "🔹 /hello  — 打招呼\n"
        "🔹 /帮助   — 显示此菜单\n"
        "🔹 /状态   — 查看系统状态\n"
        "🔹 /chat   — 与AI聊天（需要配置API）\n"
        "🔹 /搜游戏  — 搜索游戏资源\n"
        "\n"
        "💬 直接 @我 也可以聊天！"
    )
    await help_cmd.finish(msg)


# === 状态 ===
status = on_command("状态", aliases={"status", "运行状态"}, priority=10)

@status.handle()
async def handle_status():
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    msg = (
        f"🖥 **系统状态**\n"
        f"系统: {platform.system()} {platform.release()}\n"
        f"CPU: {cpu}%\n"
        f"内存: {mem.percent}% ({mem.used // 1024**3}GB / {mem.total // 1024**3}GB)\n"
        f"磁盘: {disk.percent}% ({disk.free // 1024**3}GB 可用)\n"
        f"运行时间: 正常 ✅"
    )
    await status.finish(msg)
