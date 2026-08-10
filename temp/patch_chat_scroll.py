# -*- coding: utf-8 -*-
"""修复 chat_page.py 历史消息懒加载索引 bug + 内容不足一屏时自动补历史"""
import io, sys, re

path = r"D:\7tan\7tanAI\src\ui\chat_page.py"
with io.open(path, encoding="utf-8") as f:
    text = f.read()

orig_len = len(text)

# ---------- 1. 重写 _load_more_history ----------
old_func_start = "    def _load_more_history(self):"
old_func_end_next = "    def _insert_message_at_top"
i0 = text.index(old_func_start)
i1 = text.index(old_func_end_next)
old_func = text[i0:i1]

new_func = '''    def _load_more_history(self):
        """加载更早的历史消息（每次 LAZY_CHUNK 条）"""
        if self._rendered_start <= 0:
            self._all_rendered = True
            self._lazy_loading = False
            return

        chunk = self._LAZY_CHUNK
        new_start = max(0, self._rendered_start - chunk)

        # 从完整历史列表取缺失的一段（绝对下标，保持升序）
        old_messages = []
        if self._full_history_messages:
            raw_slice = self._full_history_messages[new_start:self._rendered_start]
            for msg in raw_slice:
                role = msg.get("role", "system")
                content = msg.get("content", "")
                try:
                    html = self._pre_parse_single(content, role) if content else None
                except Exception:
                    html = None
                md = {"role": role, "content": content,
                      "timestamp": msg.get("timestamp") or msg.get("created_at", ""),
                      "cost": msg.get("cost", 0), "tool_calls": msg.get("tool_calls"),
                      "html": html}
                old_messages.append(md)

        # 为空则放弃（历史缺失）
        if not old_messages:
            self._all_rendered = True
            self._lazy_loading = False
            return

        # 同步数据列表：在 new_start 处整体插入（保持升序，修复重复/缺漏）
        self._message_data[new_start:new_start] = old_messages

        # 记录当前滚动位置，用于加载后恢复
        sb = self._scroll.verticalScrollBar()
        old_max = sb.maximum()

        self._scroll.setUpdatesEnabled(False)
        try:
            for md in old_messages:
                self._insert_message_at_top(md)

            self._rendered_start = new_start
            self._rendered_end = len(self._message_data)
            if new_start <= 0:
                self._all_rendered = True
                # 移除"加载更多"提示
                for i in range(self._messages_layout.count()):
                    w = self._messages_layout.itemAt(i).widget()
                    if w and hasattr(w, '_content') and '以上还有' in getattr(w, '_content', ''):
                        self._messages.remove(w)
                        item = self._messages_layout.takeAt(i)
                        if item.widget():
                            item.widget().deleteLater()
                        # 同步清理 _message_data
                        for j, md in enumerate(self._message_data):
                            if md.get("role") == "system" and '以上还有' in md.get("content", ""):
                                self._message_data.pop(j)
                                self._rendered_end -= 1
                                self._rendered_start -= 1
                                break
                        break
        finally:
            self._scroll.setUpdatesEnabled(True)
            self._messages_container.adjustSize()
            self._messages_container.updateGeometry()

        # 恢复滚动位置（新消息在老消息之上，需要补偿偏移）
        try:
            new_max = sb.maximum()
            delta = max(0, new_max - old_max)
            cur = sb.value()
            QTimer.singleShot(50, lambda: sb.setValue(min(sb.maximum(), cur + delta)))
        except Exception:
            pass
        self._lazy_loading = False

'''
text = text[:i0] + new_func + text[i1:]

# ---------- 2. _finish_render 末尾追加自动补历史 ----------
anchor = "        self._update_context_indicator()\n"
# 找 _finish_render 函数体内的 anchor（紧跟 valueChanged connect 之后的那处）
fin_start = text.index("    def _finish_render(self):")
fin_end = text.index("    def _on_history_scroll", fin_start)
fin_block = text[fin_start:fin_end]
# 在 _finish_render 的最后一个 _update_context_indicator() 之后插入
pos = fin_block.rindex(anchor)
add_code = (
    "        # [修复] 内容不足一屏（无滚动条）时无法靠滚动触发懒加载 → 自动补历史\n"
    "        if not self._all_rendered:\n"
    "            QTimer.singleShot(80, self._auto_fill_history)\n"
    "\n"
)
fin_block_new = fin_block[:pos + len(anchor)] + add_code + fin_block[pos + len(anchor):]
text = text[:fin_start] + fin_block_new + text[fin_end:]

# ---------- 3. 在 _on_history_scroll 前插入 _auto_fill_history 方法 ----------
ohs_start = text.index("    def _on_history_scroll(self, value: int):")
auto_fill = '''    def _auto_fill_history(self):
        """内容不足一屏时自动加载更多历史，直到可滚动或全部加载"""
        try:
            if self._all_rendered or self._lazy_loading:
                return
            sb = self._scroll.verticalScrollBar()
            if sb.maximum() > 0:
                return
            self._lazy_loading = True
            self._load_more_history()
            # 若仍然不足一屏且未加载完，继续下一批
            if not self._all_rendered and sb.maximum() <= 0:
                QTimer.singleShot(80, self._auto_fill_history)
        except Exception:
            pass

'''
text = text[:ohs_start] + auto_fill + text[ohs_start:]

with io.open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("patched, size:", orig_len, "->", len(text))

# 语法检查
import py_compile
py_compile.compile(path, doraise=True)
print("syntax OK")
