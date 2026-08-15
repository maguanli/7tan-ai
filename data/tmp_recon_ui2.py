# -*- coding: utf-8 -*-
"""侦察 7Tan WEB 版：按钮/消息区/中止按钮（结果写 JSON 文件）"""
import json, io, sys
from playwright.sync_api import sync_playwright

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"D:\7tan\7tanAI\data\tmp_recon_result.json"
result = {}

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(executable_path=EDGE, headless=True, args=["--no-proxy-server"])
    except Exception as e:
        result["launch_fail"] = repr(e)[:300]
        browser = p.chromium.launch(headless=True, args=["--no-proxy-server"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:9900/", timeout=20000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    result["chat_display"] = page.eval_on_selector("#view-chat", "el => getComputedStyle(el).display")
    btns = page.eval_on_selector_all("button", "els => els.map(e => ({id:e.id, cls:e.className, txt:(e.innerText||'').trim().slice(0,30)}))")
    result["buttons"] = btns
    # 消息区候选
    result["msg_containers"] = [m for m in ["#chatMessages", ".chat-messages", "#messages", ".messages"] if page.query_selector(m)]
    # 中止按钮候选
    for kw in ["中止", "停止", "abort", "stop"]:
        found = page.eval_on_selector_all("button", f"els => els.filter(e => (e.innerText||'').includes('{kw}')).map(e => ({{id:e.id, cls:e.className, txt:(e.innerText||'').trim()}}))")
        if found:
            result["abort_candidates_" + kw] = found
    # 发送按钮候选
    for kw in ["发送", "send"]:
        found = page.eval_on_selector_all("button", f"els => els.filter(e => (e.innerText||'').includes('{kw}')).map(e => ({{id:e.id, cls:e.className, txt:(e.innerText||'').trim()}}))")
        if found:
            result["send_candidates_" + kw] = found
    # js 版本
    try:
        result["app_js"] = page.evaluate("() => Array.from(document.querySelectorAll('script')).map(s=>s.getAttribute('src')).filter(Boolean)")
    except Exception as e:
        result["app_js_err"] = str(e)
    page.screenshot(path=r"D:\7tan\7tanAI\data\screenshots\ui_recon2.png")
    browser.close()

with io.open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("WROTE", OUT)
