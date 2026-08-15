# -*- coding: utf-8 -*-
"""诊断：发送消息后聊天区到底发生了什么"""
import json, io, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"D:\7tan\7tanAI\data\tmp_diag_result.json"
log = []
def L(msg):
    log.append(str(msg)); print(str(msg)[:500], flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=EDGE, headless=True, args=["--no-proxy-server"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    console_msgs = []
    page.on("console", lambda m: console_msgs.append(f"{m.type}: {m.text[:300]}"))
    page.on("pageerror", lambda e: console_msgs.append(f"PAGEERROR: {str(e)[:300]}"))
    page.goto("http://127.0.0.1:9900/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3500)
    L("title=" + page.title())

    # 当前选中模型
    sel = page.eval_on_selector("#chatModelSelect", "el => el.value")
    L("selected model=" + str(sel))

    page.click("#chatNew", timeout=5000)
    page.wait_for_timeout(800)
    # 填输入框 + 发送
    page.fill("#chatInput", "请用中文介绍一下你自己，200字左右。")
    page.wait_for_timeout(300)
    page.click("#chatSend", timeout=5000)
    L("sent")

    for i in range(20):
        page.wait_for_timeout(1000)
        # 聊天主区域完整文本
        txt = page.evaluate("() => { const els=[...document.querySelectorAll('#view-chat *')]; const m=document.querySelector('#chatMessages')||document.querySelector('.chat-messages')||document.querySelector('#messages'); if(m) return m.innerText; const main=document.querySelector('.main'); return main?main.innerText.slice(0,800):'NO_MAIN'; }")
        # 按钮状态
        btns = page.eval_on_selector_all("button", "els => els.map(e => (e.innerText||'').trim()).filter(t => t && (t.includes('发送')||t.includes('中止')||t.includes('停止')||t.includes('⏹')||t.includes('⏸'))).slice(0,8)")
        L(f"[{i+1}s] btns={json.dumps(btns, ensure_ascii=False)}")
        L(f"[{i+1}s] chat_txt={txt[:400]!r}")
        if "中止" in json.dumps(btns, ensure_ascii=False):
            L("STOP_BTN_APPEARED at " + str(i+1) + "s")
            break
        if "错误" in txt or "失败" in txt or "未配置" in txt or "请先" in txt:
            L("ERROR_TEXT in chat at " + str(i+1) + "s")
            break

    L("console_msgs=" + json.dumps(console_msgs, ensure_ascii=False)[:1500])
    page.screenshot(path=r"D:\7tan\7tanAI\data\screenshots\diag_chat.png")
    browser.close()

with io.open(OUT, "w", encoding="utf-8") as f:
    json.dump({"log": log}, f, ensure_ascii=False, indent=2)
L("WROTE " + OUT)
