# -*- coding: utf-8 -*-
"""中止按钮后端链路测试：创建会话 -> 流式任务 -> 调用 abort -> 验证停止"""
import requests, json, time, threading

BASE = "http://127.0.0.1:9900"

def main():
    # 1. 创建会话
    try:
        r = requests.post(f"{BASE}/api/chat/send", json={"message": "__new_session__"}, timeout=15)
        sid = r.json().get("session_id")
        print(f"[1] 创建会话: HTTP {r.status_code}, session_id={sid}")
        if not sid:
            print("   无 session_id，尝试从 history 取")
            r2 = requests.get(f"{BASE}/api/chat/history", timeout=15)
            s = (r2.json().get("sessions") or [])
            sid = s[0]["session_id"] if s else None
            print(f"   history 取到 session_id={sid}")
    except Exception as e:
        print(f"[1] 创建会话失败: {e}")
        return

    chunks = []
    stream_done = threading.Event()

    def stream_task():
        try:
            with requests.post(
                f"{BASE}/api/chat/send/stream",
                json={"session_id": sid, "message": "请写一篇关于秋天的短文，500字左右"},
                stream=True, timeout=None
            ) as resp:
                print(f"[2] 流式请求: HTTP {resp.status_code}")
                for line in resp.iter_lines(decode_unicode=True):
                    if stream_done.is_set():
                        break
                    if line and line.startswith("data:"):
                        try:
                            ev = json.loads(line[5:])
                            chunks.append(ev)
                            t = ev.get("type")
                            if t == "text_chunk":
                                pass
                            elif t == "done":
                                print("   [流] 收到 done 事件")
                            elif t == "error":
                                print("   [流] 收到 error:", ev.get("message"))
                        except Exception:
                            pass
        except Exception as e:
            print(f"[2] 流式异常: {type(e).__name__}: {str(e)[:150]}")

    t = threading.Thread(target=stream_task, daemon=True)
    t.start()

    # 2. 等待 agent 开始输出
    time.sleep(6)

    text_before = sum(len(c.get("content","")) for c in chunks if c.get("type") == "text_chunk")
    n_before = len(chunks)
    print(f"[3] abort 前: 共 {n_before} 个事件, 文本 {text_before} 字")

    # 3. 调用 abort
    try:
        r3 = requests.post(f"{BASE}/api/chat/abort/{sid}", timeout=10)
        print(f"[4] 调用 abort: HTTP {r3.status_code}, body={r3.text[:150]}")
    except Exception as e:
        print(f"[4] abort 请求失败: {e}")

    # 4. 等待观察 5 秒，看是否还有新输出
    time.sleep(5)
    stream_done.set()

    text_after = sum(len(c.get("content","")) for c in chunks if c.get("type") == "text_chunk")
    n_after = len(chunks)
    new_text = text_after - text_before
    print(f"[5] abort 后: 共 {n_after} 个事件, 文本 {text_after} 字")
    print(f"    abort 后新增文本: {new_text} 字")
    print(f"    新增事件数: {n_after - n_before}")

    # 5. 结论
    if new_text == 0:
        print("\n✅ 结论: 中止生效，abort 后无新增输出")
    else:
        print(f"\n⚠️ 结论: abort 后仍有 {new_text} 字新增输出，需检查")

if __name__ == "__main__":
    main()
