# -*- coding: utf-8 -*-
"""侦察 7Tan WEB 版聊天区 DOM，确认输入框/发送/中止按钮选择器"""
import json
from playwright.sync_api import sync_playwright

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(executable_path=EDGE, headless=True, args=["--no-proxy-server"])
    except Exception as e:
        print("EDGE_LAUNCH_FAIL:", repr(e)[:300])
        browser = p.chromium.launch(headless=True, args=["--no-proxy-server"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:9900/", timeout=20000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # 聊天视图
    chat = page.query_selector("#view-chat")
    print("view-chat exists:", bool(chat), "display:", page.eval_on_selector("#view-chat", "el => getComputedStyle(el).display") if chat else "N/A")

    # 输入框
    inputs = page.eval_on_selector_all("textarea, input", "els => els.map(e => ({id:e.id, cls:e.className, ph:e.placeholder, type:e.type}))")
    print("INPUTS:", json.dumps(inputs, ensure_ascii=False)[:800])

    # 所有按钮
    btns = page.eval_on_selector_all("button", "els => els.map(e => ({id:e.id, cls:e.className, txt:(e.innerText||'').trim().slice(0,24)}))")
    print("BUTTONS:", json.dumps(btns, ensure_ascii=False)[:1500])

    # 消息区
    msg = page.query_selector("#chatMessages, .chat-messages, #messages")
    print("msg container:", [m for m in ["#chatMessages", ".chat-messages", "#messages"] if page.query_selector(m)])

    # 页面 js 版本
    try:
        ver = page.evaluate("() => window.__webVer || document.querySelector('script[src*=app\\.js]')?.getAttribute('src') || ''")
        print("APP_JS:", ver)
    except Exception as e:
        print("ver err", e)
    page.screenshot(path=r"D:\7tan\7tanAI\data\screenshots\ui_recon.png")
    browser.close()
print("DONE")
