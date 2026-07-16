"""
游戏搜索插件 - 从七坛数据库搜索游戏资源
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot, Event
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "games.db")

search_game = on_command("搜游戏", aliases={"找游戏", "游戏搜索", "search"}, priority=10)


@search_game.handle()
async def handle_search(matcher: Matcher, args: Message = CommandArg()):
    keyword = args.extract_plain_text().strip()
    if not keyword:
        await matcher.finish("请输入游戏名称，例如: /搜游戏 崩坏")

    if not os.path.exists(DB_PATH):
        await matcher.finish("⚠️ 游戏数据库尚未建立，请先通过7tan-editor采集游戏资源")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, category, intro, download_url FROM resources "
            "WHERE title LIKE ? AND resource_type='game' LIMIT 5",
            (f"%{keyword}%",)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await matcher.finish(f"未找到与「{keyword}」相关的游戏 😢")

        result = f"🎮 搜索「{keyword}」结果:\n\n"
        for i, (title, cat, intro, url) in enumerate(rows, 1):
            short_intro = (intro or "暂无简介")[:60].replace("\n", " ")
            download = url or "暂无下载链接"
            result += f"{i}. **{title}** [{cat}]\n"
            result += f"   📝 {short_intro}...\n"
            result += f"   🔗 {download}\n\n"

        await matcher.finish(result.strip())

    except Exception as e:
        await matcher.finish(f"⚠️ 搜索出错: {e}")
