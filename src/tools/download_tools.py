"""
下载工具 — 断点续传 + 磁盘检查 + 蜘蛛模式
"""
import os
import hashlib
import random
import shutil
from pathlib import Path

import requests
from loguru import logger
from tqdm import tqdm

from .registry import register_tool
from ..utils.helpers import human_readable_size, file_md5, ensure_dir

# 搜索引擎蜘蛛 UA 池（详见架构文档 §8.3）
SPIDER_UA_POOL = {
    "googlebot_desktop": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "googlebot_smartphone": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "baiduspider_desktop": "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
    "baiduspider_mobile": "Mozilla/5.0 (Linux; Android 10; MI 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36 (compatible; Baiduspider-render/2.0; +http://www.baidu.com/search/spider.html)",
    "sogou_spider": "Sogou web spider/4.0(+http://www.sogou.com/docs/help/webmasters.htm#07)",
    "360spider": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0); 360Spider",
    "bytedance_spider": "Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)",
}


def get_spider_headers() -> dict:
    """随机获取一个蜘蛛请求头"""
    ua = random.choice(list(SPIDER_UA_POOL.values()))
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


@register_tool(
    name="download_file",
    description="下载文件到本地，支持断点续传。返回本地文件路径和 MD5。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "下载 URL"},
            "dest_dir": {"type": "string", "description": "目标目录", "default": "downloads/packages"},
            "filename": {"type": "string", "description": "文件名（可选，从 URL 推断）"},
            "use_spider": {"type": "boolean", "description": "是否伪装搜索引擎蜘蛛下载", "default": False},
        },
        "required": ["url"]
    },
    category="file",
)
def download_file(url: str, dest_dir: str = "downloads/packages",
                  filename: str = None, use_spider: bool = False) -> str:
    """下载文件，支持断点续传，返回结果说明"""
    dest_path = Path(dest_dir)
    ensure_dir(str(dest_path))

    if filename is None:
        filename = url.split("/")[-1].split("?")[0] or "download"
    local_path = dest_path / filename

    # 磁盘检查
    free_gb = shutil.disk_usage(str(dest_path)).free / (1024 ** 3)
    if free_gb < 1:
        return f"❌ 磁盘空间不足（可用 {free_gb:.1f}GB），跳过下载"

    # 构造请求
    headers = get_spider_headers() if use_spider else {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # 断点续传
    existing_size = local_path.stat().st_size if local_path.exists() else 0
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"

    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=7200)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        mode = "ab" if resp.status_code == 206 else "wb"
        if mode == "wb":
            existing_size = 0

        logger.info(f"📥 下载: {filename} ({human_readable_size(total_size + existing_size)})")

        with open(local_path, mode) as f:
            with tqdm(total=total_size, unit="B", unit_scale=True, desc=filename[:30]) as pbar:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        md5 = file_md5(local_path)
        size_str = human_readable_size(local_path.stat().st_size)
        logger.info(f"✅ 下载完成: {filename} ({size_str}, MD5: {md5[:16]}...)")

        return f"✅ 下载成功: {local_path}\n  大小: {size_str}\n  MD5: {md5}"
    except Exception as e:
        return f"❌ 下载失败: {e}"


@register_tool(
    name="check_disk",
    description="检查磁盘剩余空间，下载前必须先调用此工具确认空间足够。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "检查的路径", "default": "."},
        },
        "required": []
    },
    category="monitor",
)
def check_disk(path: str = ".") -> str:
    """检查磁盘空间"""
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    used_percent = (usage.used / usage.total) * 100
    return f"💾 磁盘空间: {free_gb:.1f}GB 可用 / {total_gb:.1f}GB 总计 (已用 {used_percent:.1f}%)"
