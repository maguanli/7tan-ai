# -*- coding: utf-8 -*-
"""实测 WEB 版「中止」按钮：发长任务 -> 点击中止 -> 验证 UI 状态"""
import json, io, time, sys
from playwright.sync_api import sync_playwright

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"D:\7tan\7tanAI\data\tmp_abort_test_result.json"
log = []

def L(msg):
    log.append(str(msg))
    print(msg, flush=True)

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(executable_path=EDGE, headless=True, args=["--no-proxy-server"])
        L("browser: EDGE headless OK")
    except Exception as e:
        L("EDGE_LAUNCH_FAIL " + repr(e)[:200])
        browser = p.chromium.launch(headless=True, args=["--no-proxy-server"])
        L("browser: chromium headless OK")

    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:9900/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3500)
    L("page loaded, title=" + page.title())

    # 模型下拉
    try:
        opts = page.eval_on_selector_all("#chatModelSelect option", "els => els.map(o => o.value + '|' + o.textContent.trim())")
        L("models: " + json.dumps(opts, ensure_ascii=False)[:300])
    except Exception as e:
        L("model select err: " + repr(e)[:150])

    # 新对话
    try:
        page.click("#chatNew", timeout=5000)
        L("clicked #chatNew")
    except Exception as e:
        L("chatNew err: " + repr(e)[:150])

    # 输入消息（要求生成长回复，便于测试中止）
    msg_text = "请详细介绍这个7tanAI系统的整体架构、所有模块的功能和作用，尽可能详细全面，用中文回答。"
    try:
        page.fill("#chatInput", msg_text)
        L("filled chatInput")
    except Exception as e:
        L("fill err: " + repr(e)[:200])

    # 点击发送
    t0 = time.time()
    try:
        page.click("#chatSend", timeout=5000)
        L("clicked #chatSend")
    except Exception as e:
        L("send err: " + repr(e)[:200])

    # 轮询等待输出开始（出现消息内容或按钮变化），最多 30s
    started = False
    for i in range(30):
        page.wait_for_timeout(1000)
        btns = page.eval_on_selector_all("button", "els => els.map(e => (e.innerText||'').trim()).filter(t => t)")
        send_txt = ""
        stop_txt = ""
        for t in btns:
            if "发送" in t or "▲" in t:
                send_txt = t
            if "中止" in t or "停止" in t:
                stop_txt = t
        # 消息区文本
        body_txt = page.evaluate("() => { const m=document.querySelector('#chatMessages, .chat-messages, #messages, .messages'); return m ? m.innerText.slice(-400) : ''; }")
        if stop_txt or (body_txt and len(body_txt.strip()) > 5):
            started = True
            L(f"[{i+1}s] send_btn='{send_txt}' stop_btn='{stop_txt}' msg_tail={body_txt[-120:]!r}")
            break
        if i in (0, 2, 5, 10, 15, 20, 25):
            L(f"[{i+1}s] send_btn='{send_txt}' stop_btn='{stop_txt}'")

    if not started:
        L("RESULT: 30s 内未见输出开始，中止按钮未出现")
    else:
        # 再等 2 秒让输出积累
        page.wait_for_timeout(2000)
        btns = page.eval_on_selector_all("button", "els => els.map(e => (e.innerText||'').trim()).filter(t => t)")
        stop_btn_found = [t for t in btns if "中止" in t or "停止" in t]
        L("before abort, buttons with 中止/停止: " + json.dumps(stop_btn_found, ensure_ascii=False))

        # 点击中止按钮
        clicked = False
        if stop_btn_found:
            try:
                # 优先找 id=chatStop 或含"中止/停止"文本的按钮
                page.click("#chatStop", timeout=3000)
                clicked = True
                L("clicked #chatStop")
            except Exception:
                try:
                    page.click("button:has-text('中止')", timeout=3000)
                    clicked = True
                    L("clicked button:has-text('中止')")
                except Exception:
                    try:
                        page.click("button:has-text('停止')", timeout=3000)
                        clicked = True
                        L("clicked button:has-text('停止')")
                    except Exception as e:
                        L("click stop btn err: " + repr(e)[:200])
        else:
            L("no stop button found!!")

        if clicked:
            page.wait_for_timeout(1500)
            btns2 = page.eval_on_selector_all("button", "els => els.map(e => (e.innerText||'').trim()).filter(t => t)")
            send_txt2 = [t for t in btns2 if "发送" in t or "▲" in t]
            stop_txt2 = [t for t in btns2 if "中止" in t or "停止" in t]
            body_txt2 = page.evaluate("() => { const m=document.querySelector('#chatMessages, .chat-messages, #messages, .messages'); return m ? m.innerText.slice(-500) : ''; }")
            L("AFTER abort: send_btn=" + json.dumps(send_txt2, ensure_ascii=False))
            L("AFTER abort: stop_btn=" + json.dumps(stop_txt2, ensure_ascii=False))
            L("AFTER abort: msg_tail=" + body_txt2[-300:])
            # 再等 3 秒看是否还在输出
            page.wait_for_timeout(3000)
            body_txt3 = page.evaluate("() => { const m=document.querySelector('#chatMessages, .chat-messages, #messages, .messages'); return m ? m.innerText.slice(-500) : ''; }")
            L("AFTER +3s: msg_tail=" + body_txt3[-300:])
            L("GROWTH_CHECK: len_before=%d len_after=%d" % (len(body_txt2), len(body_txt3)))
            page.screenshot(path=r"D:\7tan\7tanAI\data\screenshots\abort_test_after.png")

    browser.close()

with io.open(OUT, "w", encoding="utf-8") as f:
    json.dump({"log": log}, f, ensure_ascii=False, indent=2)
L("WROTE " + OUT)
