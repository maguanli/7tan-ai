# -*- coding: utf-8 -*-
"""
desktop_bot — Linux 平台变体（由 7Tan 平台适配器自动复制启用）

本文件是 desktop_bot 插件在 Linux（含鸿蒙PC Linux生态）上的替代实现：
  - 所有平台专属 import 均 try/except 包裹（保证导入自测通过）
  - 功能缺失时返回明确错误提示，引导安装依赖
  - 与 Windows 版 tools.py 保持同名工具函数（desktop_xxx），上层调用无需改动

依赖（pip 安装）：
    pyautogui mss Pillow pytesseract
系统依赖：
    tesseract（OCR）：sudo apt install tesseract-ocr tesseract-ocr-chi-sim
    xdotool / wmctrl（窗口与键鼠）：sudo apt install xdotool wmctrl xclip
注意：
    Linux 桌面环境需 X11（Wayland 下部分功能受限，建议 x11 会话）
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

_PLATFORM = platform.system()  # Linux


def _err(msg: str) -> dict:
    return {"ok": False, "error": msg}


def _sh(cmd: list, timeout: int = 15) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or "").strip()
    except Exception as e:
        return f"[执行失败] {e}"


# ============================================================
# 环境检查
# ============================================================
def desktop_env_check():
    """检查 Linux 桌面自动化依赖是否就绪"""
    report = {
        "platform": _PLATFORM,
        "mss": mss is not None,
        "PIL": Image is not None,
        "pyautogui": pyautogui is not None,
        "pytesseract": pytesseract is not None,
        "tesseract_bin": bool(_sh(["which", "tesseract"])),
        "xdotool": bool(_sh(["which", "xdotool"])),
        "wmctrl": bool(_sh(["which", "wmctrl"])),
    }
    missing = [k for k, v in report.items() if not v and k not in ("platform",)]
    report["ready"] = not missing
    report["suggest"] = (
        "请安装依赖：pip install pyautogui mss Pillow pytesseract\n"
        "并安装系统工具：sudo apt install xdotool wmctrl xclip tesseract-ocr tesseract-ocr-chi-sim"
        if missing else "环境就绪"
    )
    return report


# ============================================================
# 窗口列表 / 激活（wmctrl + xdotool）
# ============================================================
def desktop_windows(keyword: str = ""):
    """列出当前窗口（wmctrl -l）"""
    out = _sh(["wmctrl", "-l"])
    if not out or out.startswith("[执行失败]"):
        return _err(f"无法获取窗口列表（请安装 wmctrl）: {out}")
    names = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 4:
            names.append(parts[3])
        elif parts:
            names.append(parts[-1])
    if keyword:
        names = [n for n in names if keyword.lower() in n.lower()]
    return {"ok": True, "windows": names, "count": len(names)}


def desktop_activate(title: str):
    """激活指定窗口（wmctrl -a 模糊激活）"""
    out = _sh(["wmctrl", "-a", title])
    if out.startswith("[执行失败]") or "error" in out.lower():
        return _err(f"无法激活窗口 {title}: {out}")
    return {"ok": True, "activated": title}


# ============================================================
# 截图（mss）
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
                Image.frombytes("RGB", shot.size, shot.rgb).save(save)
            else:
                mss.tools.to_png(shot.rgb, shot.size, output=save)
            return {"ok": True, "path": save}
    except Exception as e:
        return _err(f"截图失败: {e}")


# ============================================================
# OCR（tesseract）
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
        return _err(f"OCR 失败（请确认已安装 tesseract：sudo apt install tesseract-ocr tesseract-ocr-chi-sim）：{e}")


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
    try:
        data = pytesseract.image_to_data(Image.open(shot["path"]), output_type=pytesseract.Output.DICT)
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
    """组合键，如 ctrl,f / alt,tab / enter"""
    if pyautogui is None:
        return _err("缺少依赖 pyautogui")
    try:
        parts = [p.strip() for p in keys.split(",") if p.strip()]
        if parts[-1].lower() in ("enter", "return"):
            pyautogui.press("enter")
        else:
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
# 剪贴板（xclip）
# ============================================================
def desktop_paste_image(path: str, pos: str = ""):
    """粘贴图片到当前焦点（Linux 剪贴板为文件路径提示，可配合应用粘贴）"""
    if not os.path.exists(path):
        return _err(f"图片不存在: {path}")
    if pos:
        r = desktop_click_pos(pos)
        if not r.get("ok"):
            return r
        time.sleep(0.2)
    # 将图片二进制写入剪贴板（xclip -selection clipboard -t image/png）
    try:
        with open(path, "rb") as f:
            data = f.read()
        proc = subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-i"],
                              input=data, timeout=10)
        if proc.returncode != 0:
            return _err("写入剪贴板失败（请安装 xclip）")
    except Exception as e:
        return _err(f"剪贴板失败: {e}")
    return {"ok": True, "path": path, "note": "已复制到剪贴板，请在目标应用内按 Ctrl+V 粘贴"}


# ============================================================
# 发送聊天（微信 Linux 版基础流程：激活 → 搜索 → 输入 → 回车）
# ============================================================
def desktop_send_chat(window: str, search: str, message: str, hotkey: str = "ctrl,f"):
    """在 Linux 聊天应用发送消息（基础版：激活窗口 → 搜索对象 → 输入 → 回车）"""
    r = desktop_activate(window)
    if not r.get("ok"):
        return r
    time.sleep(0.5)
    if pyautogui:
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.5)
        pyautogui.typewrite(search)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.5)
        pyautogui.typewrite(message)
        time.sleep(0.2)
        pyautogui.press("enter")
    return {"ok": True, "sent": f"{window} → {search}: {message[:40]}"}


# ============================================================
# 兼容占位（Windows 专属能力在 Linux 上不可用，给出明确提示）
# ============================================================
def desktop_uia(title: str = "", depth: int = 4, top: int = 80):
    """UI 自动化控件树（Linux 无 pywinauto，暂不可用）"""
    return _err("Linux 暂不支持 UI 控件树（pywinauto 为 Windows 专属），请使用 OCR 方式操作界面")


def desktop_tmatch(template: str, region: str = "", threshold: float = 0.8, max_matches: int = 5):
    """模板匹配（Linux 基础版：OpenCV 可选）"""
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
        "note": "Linux 基础版快照（窗口名 + OCR 文本）",
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
        "note": "Linux 基础版（截图+OCR）；如需视觉语义理解请在 7Tan WEB 版使用 cloud 视觉工具",
    }


# 导出工具列表（供插件框架注册）
TOOLS = [
    desktop_env_check, desktop_windows, desktop_snapshot, desktop_activate,
    desktop_screenshot, desktop_ocr, desktop_see, desktop_uia, desktop_tmatch,
    desktop_click_text, desktop_click_pos, desktop_type_text, desktop_paste_image,
    desktop_hotkey, desktop_verify, desktop_send_chat,
]
