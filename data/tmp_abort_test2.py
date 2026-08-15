# -*- coding: utf-8 -*-
"""实测 WEB 版「中止」按钮 v2：等待会话就绪 -> 发送长任务 -> 点击中止 -> 验证"""
import json, io, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"D:\7tan\7tanAI\data\tmp_abort_test2_result.json"
log = []
def L(msg):
    log.append(str(msg)); print(str(msg)[:600], flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=EDGE, headless=True, args=["--no-proxy-server"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    toasts = []
    page.on("console", lambda m: toasts.append(f"{m.type}: {m.text[:200]}") if m.type in ("error","warning") else None)
    page.goto("http://127.0.0.1:9900/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3500)
    L("title=" + page.title())

    # 1) 点击新对话，轮询等待 curSession 就绪（最多 15s）
    page.click("#chatNew", timeout=5000)
    session_ok = False
    for i in range(15):
        page.wait_for_timeout(1000)
        try:
            cur = page.evaluate("typeof curSession !== 'undefined' ? curSession : 'UNDEF'")
        except Exception as e:
            cur = "ERR:" + str(e)[:50]
        sess_items = page.eval_on_selector_all("#sessionList .session-item, #sessionList button", "els => els.length")
        L(f"[wait-session {i+1}s] curSession={cur} session_items={sess_items}")
        if cur and cur != "UNDEF" and cur != "ERR:" and sess_items:
            session_ok = True
            L("SESSION READY: " + str(cur))
            break
    if not session_ok:
        L("RESULT: 会话未就绪，中止")

    # 2) 填充输入框并发送
    page.fill("#chatInput", "请用中文详细介绍7tanAI系统的整体架构和所有功能模块，写一篇2000字的完整介绍。")
    page.wait_for_timeout(300)
    page.click("#chatSend", timeout=5000)
    L("sent")

    # 3) 等待「中止」按钮出现（输出开始）
    stop_seen = False
    for i in range(40):
        page.wait_for_timeout(1000)
        btn_txts = page.eval_on_selector_all("#chatSend", "els => els.map(e => (e.innerText||'').trim())")
        send_btn = btn_txts[0] if btn_txts else ""
        body = page.evaluate("() => { const m=document.querySelector('#chatMessages'); return m ? m.innerText.slice(-300) : ''; }")
        if i % 3 == 0 or "中止" in send_btn:
            L(f"[{i+1}s] send_btn={send_btn!r} msg_tail={body[-120:]!r}")
        if "中止" in send_btn:
            stop_seen = True
            L("STOP_BTN_APPEARED at " + str(i+1) + "s")
            break
    if not stop_seen:
        L("RESULT: 40s 内未出现中止按钮（输出可能未开始或已完成）")
        L("final_btn=" + send_btn)
        L("final_msg_tail=" + body[-300:])
    else:
        # 4) 等 2 秒积累输出，记录长度
        page.wait_for_timeout(2000)
        before_len = page.evaluate("() => { const m=document.querySelector('#chatMessages'); return m ? m.innerText.length : 0; }")
        # 5) 点击中止
        page.click("#chatSend", timeout=5000)
        L("clicked abort (#chatSend)")
        page.wait_for_timeout(1200)
        btn_after = page.eval_on_selector_all("#chatSend", "els => els.map(e => (e.innerText||'').trim())")
        L("AFTER abort send_btn=" + repr(btn_after[0] if btn_after else ""))
        after1_len = page.evaluate("() => { const m=document.querySelector('#chatMessages'); return m ? m.innerText.length : 0; }")
        body_after = page.evaluate("() => { const m=document.querySelector('#chatMessages'); return m ? m.innerText.slice(-400) : ''; }")
        L("AFTER abort msg_tail=" + body_after[-250:])
        # 6) 再等 4 秒，确认输出不再增长
        page.wait_for_timeout(4000)
        after2_len = page.evaluate("() => { const m=document.querySelector('#chatMessages'); return m ? m.innerText.length : 0; }")
        body_after2 = page.evaluate("() => { const m=document.querySelector('#chatMessages'); return m ? m.innerText.slice(-400) : ''; }")
        L("AFTER +4s msg_tail=" + body_after2[-250:])
        L(f"GROWTH: before={before_len} after1s={after1_len} after5s={after2_len}")
        if after2_len == after1_len:
            L("VERDICT: ✅ 输出已停止（中止生效）")
        else:
            L("VERDICT: ❌ 输出仍在增长（中止未生效）")
        page.screenshot(path=r"D:\7tan\7tanAI\data\screenshots\abort_test2_after.png")

    L("toasts=" + json.dumps(toasts, ensure_ascii=False)[:800])
    browser.close()

with io.open(OUT, "w", encoding="utf-8") as f:
    json.dump({"log": log}, f, ensure_ascii=False, indent=2)
L("WROTE " + OUT)
