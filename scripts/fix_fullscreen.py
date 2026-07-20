"""
Fix player.py: Replace broken hwnd-switch fullscreen with VLC native set_fullscreen.
"""
import re

with open('src/ui/video_editor/player.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the fullscreen section: starts with "#  全屏" comment block
marker = '\n    # ==================================================================\n    #  全屏\n    # =================================================================='
idx = content.find(marker)
if idx == -1:
    print("ERROR: marker not found")
    exit(1)

# Find where it ends: "def closeEvent"
end_marker = '\n    def closeEvent(self, event):'
end_idx = content.find(end_marker, idx + len(marker))
if end_idx == -1:
    print("ERROR: end_marker not found")
    exit(1)

print(f"Replacing bytes {idx} to {end_idx} ({end_idx - idx} bytes)")

new_fs = """
    # ==================================================================
    #  全屏（VLC 原生 set_fullscreen - 不切换 hwnd，最可靠）
    # ==================================================================

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_btn_fullscreen') and hasattr(self, '_player_container'):
            pw = self._player_container.width()
            self._btn_fullscreen.move(pw - 48, 8)
            self._btn_fullscreen.raise_()

    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        if not self._media_player:
            return

        self._is_fullscreen = True
        self._btn_fullscreen.set_fullscreen_state(True)

        try:
            self._media_player.set_fullscreen(True)
        except Exception as e:
            logger.warning(f"VLC set_fullscreen(True): {e}")
            self._is_fullscreen = False
            self._btn_fullscreen.set_fullscreen_state(False)
            return

        if not hasattr(self, '_fs_poll_timer'):
            self._fs_poll_timer = QTimer(self)
            self._fs_poll_timer.setInterval(400)
            self._fs_poll_timer.timeout.connect(self._poll_fullscreen_state)
        self._fs_poll_timer.start()

        logger.info("VLC native fullscreen ON")

    def _poll_fullscreen_state(self):
        if not self._media_player or not self._is_fullscreen:
            self._stop_fs_poll()
            return
        try:
            if not self._media_player.get_fullscreen():
                self._is_fullscreen = False
                self._btn_fullscreen.set_fullscreen_state(False)
                self._stop_fs_poll()
                logger.info("VLC fullscreen exited (user)")
        except Exception:
            pass

    def _stop_fs_poll(self):
        if hasattr(self, '_fs_poll_timer') and self._fs_poll_timer is not None:
            try:
                self._fs_poll_timer.stop()
            except Exception:
                pass

    def _exit_fullscreen(self):
        self._is_fullscreen = False
        self._btn_fullscreen.set_fullscreen_state(False)
        self._stop_fs_poll()

        if self._media_player:
            try:
                self._media_player.set_fullscreen(False)
            except Exception as e:
                logger.warning(f"VLC set_fullscreen(False): {e}")

        logger.info("Fullscreen OFF (button)")

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)
"""

new_content = content[:idx] + new_fs + content[end_idx:]

with open('src/ui/video_editor/player.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"OK: {len(content)} -> {len(new_content)} bytes")
