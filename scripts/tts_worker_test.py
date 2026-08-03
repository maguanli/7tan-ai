# -*- coding: utf-8 -*-
"""新流式 worker 逻辑功能测试（模拟，不依赖真实 TTS/UI）"""
import sys, os, queue, threading, time
sys.path.insert(0, r'D:\7tan\7tanAI')

# 模拟 ChatPage 的最小对象，验证 worker 收尾判定
class FakePage:
    def __init__(self):
        self._tts_stream_queue = queue.Queue()
        self._tts_stream_ok_count = 0
        self._tts_streamed_this_reply = False
        self._tts_stream_done_ts = 0.0
        self._streaming_text = "你好。这是测试回复。"
        self.fallback_called = []
        self.tts_notice = []

    def tts_notice_signal(self):
        return self

    def emit(self, msg):
        self.tts_notice.append(msg)

    # 复刻新 worker 逻辑（从 chat_page 提取）
    def _tts_stream_worker(self, engine_success):
        total = 0
        while True:
            sentence = self._tts_stream_queue.get()
            if sentence is None:
                self._tts_stream_done_ts = time.time()
                if self._tts_stream_ok_count > 0:
                    self._tts_streamed_this_reply = True
                else:
                    full = getattr(self, "_streaming_text", "") or ""
                    if full.strip():
                        self._tts_stream_done_ts = 0.0
                        self.fallback_called.append(full)
                break
            total += 1
            # 模拟 tts_speak 结果
            result = {"status": "ok"} if engine_success else {"status": "error", "message": "引擎失败"}
            if result.get("status") == "ok":
                self._tts_stream_ok_count += 1

    def run(self, engine_success, sentences):
        for s in sentences:
            self._tts_stream_queue.put(s)
        self._tts_stream_queue.put(None)
        t = threading.Thread(target=self._tts_stream_worker, args=(engine_success,))
        t.start(); t.join(timeout=10)

# 场景1：引擎全失败 → 必须全文兜底，不置防重标记
p1 = FakePage()
p1.run(engine_success=False, sentences=["第一句。", "第二句。"])
print("场景1 全失败:", "兜底朗读=", len(p1.fallback_called) == 1,
      "| 防重标记=", p1._tts_streamed_this_reply, "(应False)",
      "| done_ts重置=", p1._tts_stream_done_ts == 0.0)
assert len(p1.fallback_called) == 1 and not p1._tts_streamed_this_reply

# 场景2：部分成功 → 置防重标记，不兜底
p2 = FakePage()
p2.run(engine_success=True, sentences=["第一句。", "第二句。"])
print("场景2 部分成功:", "兜底=", len(p2.fallback_called) == 0,
      "| 防重标记=", p2._tts_streamed_this_reply, "(应True)",
      "| 成功数=", p2._tts_stream_ok_count, "(应2)")
assert p2._tts_stream_ok_count == 2 and p2._tts_streamed_this_reply and not p2.fallback_called

# 场景3：0 句（纯代码无句子）→ 兜底
p3 = FakePage()
p3._streaming_text = "```python\nprint(1)\n```"
p3.run(engine_success=True, sentences=[])
print("场景3 无句子:", "兜底=", len(p3.fallback_called) == 1, "| 防重=", p3._tts_streamed_this_reply, "(应False)")
assert len(p3.fallback_called) == 1 and not p3._tts_streamed_this_reply

print()
print("=== 全部 3 场景通过 ===")
