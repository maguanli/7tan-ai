# -*- coding: utf-8 -*-
"""
desktop_bot — macOS 平台变体（由 7Tan 平台适配器自动复制启用）

本文件是 desktop_bot 插件在 macOS 上的替代实现：
  - 所有平台专属 import 均 try/except 包裹（保证导入自测通过，不因缺依赖崩溃）
  - 功能缺失时返回明确错误提示，引导安装依赖/开启权限
  - 与 Windows 版 tools.py 保持同名工具函数（desktop_xxx），上层调用无需改动

依赖（pip 安装）：
    pyautogui mss Pillow pytesseract
系统依赖：
    tesseract（OCR）：brew install tesseract
权限：
    系统设置 → 隐私与安全性 → 辅助功能：允许终端/7Tan 控制电脑
"""
import sys
import os
import time
import json
import subprocess
import platform
from pathlib import Path

try:
    import mss
except Exception:
    mss = None
try:
    from PIL import Image
except Exception:
    Image = None
try:
    import pyautogui
except Exception:
    pyautogui = None
try:
    import pytesseract
except Exception:
    pytesseract = None

_PLATFORM = platform.system()  # Darwin / Linux / Windows


def _err(msg: str) -> dict:
    return {"ok": False, "error": msg}


def _sh(cmd: list, timeout: int = 15) -> str:
    """执行外部命令，返回 stdout（含错误兜底）"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or "").strip()
    except Exception as e:
        return f"[执行失败] {e}"


# ============================================================
# 环境检查
# ============================================================
def desktop_env_check():
    """检查 macOS 桌面自动化依赖是否就绪"""
    report = {
        "platform": _PLATFORM,
        "mss": mss is not None,
        "PIL": Image is not None,
        "pyautogui": pyautogui is not None,
        "pytesseract": pytesseract is not None,
        "tesseract_bin": bool(_sh(["which", "tesseract"])),
    }
    missing = [k for k, v in report.items() if not v and k != "platform"]
    report["ready"] = not missing
    report["suggest"] = (
        "请安装依赖：pip install pyautogui mss Pillow pytesseract\n"
        "并安装系统 OCR：brew install tesseract\n"
        "并授予「辅助功能」权限：系统设置 → 隐私与安全性 → 辅助功能"
        if missing else "环境就绪"
    )
    return report


# ============================================================
# 窗口列表 / 激活
# ============================================================
def desktop_windows(keyword: str = ""):
    """列出当前可见窗口（macOS 用 AppleScript）"""
    script = (
        'tell application "System Events" to get name of every window '
        'of (every process whose background only is false)'
    )
    out = _sh(["osascript", "-e", script])
    if not out or out.startswith("[执行失败]"):
        return _err(f"无法获取窗口列表: {out}")
    names = [n.strip() for n in out.split(",") if n.strip()]
    if keyword:
        names = [n for n in names if keyword.lower() in n.lower()]
    return {"ok": True, "windows": names, "count": len(names)}


def desktop_activate(title: str):
    """激活指定窗口（按标题模糊匹配，AppleScript）"""
    script = (
        f'tell application "System Events" to set frontmost of '
        f'(first process whose name contains "{title}") to true'
    )
    out = _sh(["osascript", "-e", script])
    if out.startswith("[执行失败]") or "error" in out.lower():
        # 尝试直接 activate 应用
        script2 = f'tell application "{title}" to activate'
        out2 = _sh(["osascript", "-e", script2])
        if out2.startswith("[执行失败]"):
            return _err(f"无法激活窗口 {title}: {out2}")
    return {"ok": True, "activated": title}


# ============================================================
# 截图
# ============================================================
def desktop_screenshot(save: str = "", region: str = ""):
    """截屏：全屏或指定区域 x,y,w,h"""
    if mss is None:
        return _err("缺少依赖 mss，请执行：pip install mss")
    try:
        with mss.mss() as sct:
            if region:
                x, y, w, h = (int(v) for v in region.replace(",", " ").split())
                monitor = {"left": x, "top": y, "width": w, "height": h}
            else:
                monitor = sct.monitors[0]
            shot = sct.grab(monitor)
            if not save:
                save = str(Path.home() / "Desktop" / f"7tan_shot_{int(time.time())}.png")
            os.makedirs(os.path.dirname(save) or ".", exist_ok=True)
            if Image is not None:
                img = Image.frombytes("RGB", shot.size, shot.rgb)
                img.save(save)
            else:
                mss.tools.to_png(shot.rgb, shot.size, output=save)
            return {"ok": True, "path": save}
    except Exception as e:
        return _err(f"截图失败: {e}")


# ============================================================
# OCR
# ============================================================
def desktop_ocr(region: str = "", engine: str = "auto"):
    """屏幕 OCR（pytesseract）"""
    if pytesseract is None:
        return _err("缺少依赖 pytesseract，请执行：pip install pytesseract")
    shot = desktop_screenshot(save="", region=region)
    if not shot.get("ok"):
        return shot
    try:
        text = pytesseract.image_to_string(shot["path"], lang="chi_sim+eng")
        return {"ok": True, "text": text.strip(), "lines": [l for l in text.splitlines() if l.strip()][:50]}
    except Exception as e:
        return _err(f"OCR 失败（请确认已安装 tesseract：brew install tesseract，并安装中文包）：{e}")


# ============================================================
# 鼠标 / 键盘（pyautogui）
# ============================================================
def desktop_click_pos(pos: str, double: bool = False):
    """按坐标点击 x,y"""
    if pyautogui is None:
        return _err("缺少依赖 pyautogui，请执行：pip install pyautogui")
    try:
        x, y = (int(v) for v in pos.replace(",", " ").split())
        pyautogui.click(x, y, clicks=2 if double else 1)
        return {"ok": True, "clicked": (x, y), "double": double}
    except Exception as e:
        return _err(f"点击失败: {e}")


def desktop_click_text(text: str, region: str = "", exclude: str = ""):
    """按文字定位点击（OCR 找文字 → 点击中心）"""
    shot = desktop_screenshot(save="", region=region)
    if not shot.get("ok"):
        return shot
    ocr = desktop_ocr(region=region)
    if not ocr.get("ok"):
        return ocr
    # 简化实现：pytesseract 用 image_to_data 拿坐标
    try:
        import pytesseract as pt
        data = pt.image_to_data(Image.open(shot["path"]), output_type=pt.Output.DICT)
        targets = [t for t in text.split("|") if t]
        for i, word in enumerate(data["text"]):
            if not word.strip():
                continue
            for t in targets:
                if t in word and not (exclude and exclude in word):
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    return desktop_click_pos(f"{x},{y}")
        return _err(f"未在屏幕上找到文字: {text}")
    except Exception as e:
        return _err(f"定位失败: {e}")


def desktop_type_text(text: str, pos: str = ""):
    """输入文本（先点击 pos 再输入）"""
    if pyautogui is None:
        return _err("缺少依赖 pyautogui")
    try:
        if pos:
            r = desktop_click_pos(pos)
            if not r.get("ok"):
                return r
            time.sleep(0.2)
        pyautogui.typewrite(text)
        return {"ok": True, "typed": text[:50]}
    except Exception as e:
        return _err(f"输入失败: {e}")


def desktop_hotkey(keys: str):
    """组合键，如 ctrl,f / cmd,c / enter"""
    if pyautogui is None:
        return _err("缺少依赖 pyautogui")
    try:
        parts = [p.strip() for p in keys.split(",") if p.strip()]
        if parts[-1].lower() in ("enter", "return"):
            pyautogui.press("enter")
        else:
            # macOS 上把 ctrl 保留，win 快捷键自动映射 cmd
            pyautogui.hotkey(*parts)
        return {"ok": True, "hotkey": parts}
    except Exception as e:
        return _err(f"按键失败: {e}")


def desktop_verify(text: str, region: str = ""):
    """验证屏幕上是否出现指定文字"""
    ocr = desktop_ocr(region=region)
    if not ocr.get("ok"):
        return ocr
    found = [t for t in text.split("|") if t and t in ocr.get("text", "")]
    return {"ok": bool(found), "found": found, "missed": [t for t in text.split("|") if t and t not in found]}


# ============================================================
# 剪贴板（pbcopy）
# ============================================================
def desktop_paste_image(path: str, pos: str = ""):
    """粘贴图片到当前焦点（macOS 剪贴板为文件路径提示，可配合应用粘贴）"""
    if not os.path.exists(path):
        return _err(f"图片不存在: {path}")
    if pos:
        r = desktop_click_pos(pos)
        if not r.get("ok"):
            return r
        time.sleep(0.2)
    # macOS 将图片复制到剪贴板
    _sh(["osascript", "-e", f'set the clipboard to (read (POSIX file "{path}") as «class PNGf»)' if path.lower().endswith(".png") else f'set the clipboard to (read (POSIX file "{path}") as JPEG picture)'])
    return {"ok": True, "path": path, "note": "已复制到剪贴板，请在目标应用内按 Cmd+V 粘贴"}


# ============================================================
# 发送聊天（微信/QQ mac 版基础流程：激活 → 粘贴 → 回车）
# ============================================================
def desktop_send_chat(window: str, search: str, message: str, hotkey: str = "cmd,f"):
    """在 macOS 聊天应用发送消息（基础版：激活窗口 → 搜索对象 → 输入 → 回车）"""
    r = desktop_activate(window)
    if not r.get("ok"):
        return r
    time.sleep(0.5)
    pyautogui.hotkey("command", "f") if pyautogui else None
    time.sleep(0.5)
    pyautogui.typewrite(search) if pyautogui else None
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.typewrite(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    return {"ok": True, "sent": f"{window} → {search}: {message[:40]}"}


# ============================================================
# 兼容占位（Windows 专属能力在 macOS 上不可用，给出明确提示）
# ============================================================
def desktop_uia(title: str = "", depth: int = 4, top: int = 80):
    """UI 自动化控件树（macOS 无 pywinauto，暂不可用）"""
    return _err("macOS 暂不支持 UI 控件树（pywinauto 为 Windows 专属），请使用 OCR 方式操作界面")


def desktop_tmatch(template: str, region: str = "", threshold: float = 0.8, max_matches: int = 5):
    """模板匹配（macOS 基础版：OpenCV 可选，未安装时提示）"""
    try:
        import cv2
        import numpy as np
    except Exception:
        return _err("缺少依赖 opencv-python，请执行：pip install opencv-python numpy")
    try:
        shot = desktop_screenshot(save="")
        if not shot.get("ok"):
            return shot
        img = cv2.imread(shot["path"])
        templ = cv2.imread(template)
        if img is None or templ is None:
            return _err("图片读取失败")
        res = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        matches = [{"x": int(pt[0] + templ.shape[1] / 2), "y": int(pt[1] + templ.shape[0] / 2),
                    "score": round(float(res[pt[1], pt[0]]), 3)}
                   for pt in zip(*loc[::-1])][:max_matches]
        return {"ok": True, "matches": matches, "count": len(matches)}
    except Exception as e:
        return _err(f"模板匹配失败: {e}")


def desktop_snapshot(top: int = 12, ocr_top: int = 25, region: str = ""):
    """桌面结构化快照：窗口列表 + OCR 摘要"""
    wins = desktop_windows()
    ocr = desktop_ocr(region=region)
    return {
        "ok": True,
        "windows": wins.get("windows", [])[:top],
        "ocr_lines": ocr.get("lines", [])[:ocr_top] if ocr.get("ok") else [],
        "note": "macOS 基础版快照（窗口名 + OCR 文本）",
    }


def desktop_see(region: str = "", save: str = "", engine: str = "smart", vlm: bool = True):
    """看懂屏幕：截图 + OCR（视觉大模型理解需 7Tan 云端视觉能力，本地版返回 OCR 结果）"""
    shot = desktop_screenshot(save=save, region=region)
    if not shot.get("ok"):
        return shot
    ocr = desktop_ocr(region=region)
    return {
        "ok": True,
        "screenshot": shot.get("path"),
        "ocr_text": ocr.get("text", "") if ocr.get("ok") else "",
        "note": "macOS 基础版（截图+OCR）；如需视觉语义理解请在 7Tan WEB 版使用 cloud 视觉工具",
    }


# 导出工具列表（供插件框架注册）
TOOLS = [
    desktop_env_check, desktop_windows, desktop_snapshot, desktop_activate,
    desktop_screenshot, desktop_ocr, desktop_see, desktop_uia, desktop_tmatch,
    desktop_click_text, desktop_click_pos, desktop_type_text, desktop_paste_image,
    desktop_hotkey, desktop_verify, desktop_send_chat,
]
