"""Fix player.py fullscreen section"""
filepath = r"D:\7tan\7tanAI\src\ui\video_editor\player.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    # ==================================================================
    #  全屏（VLC 原生 set_fullscreen - 不切换 hwnd，最可靠）
    # ==================================================================

    def toggle_fullscreen(self):
        """切换全屏（供外部：控制栏按钮/双击/快捷键）"""
        if self._is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        """进入全屏：优先 toggle_fullscreen，失败则 set_fullscreen"""
        if not self._media_player:
            return

        self._is_fullscreen = True

        try:
            self._media_player.toggle_fullscreen()
        except Exception as e:
            logger.warning(f"VLC toggle_fullscreen exception: {e}")
            self._is_fullscreen = False
            return

        # 验证是否真的进入了全屏
        import time as _time
        _time.sleep(0.15)
        try:
            if not self._media_player.get_fullscreen():
                logger.warning("get_fullscreen=False, trying set_fullscreen(True)")
                self._media_player.set_fullscreen(True)
                _time.sleep(0.1)
                if not self._media_player.get_fullscreen():
                    self._is_fullscreen = False
                    logger.error("Cannot enter fullscreen!")
        except Exception:
            pass

        # 轮询检测用户手动退出（ESC / VLC 双击）
        if not hasattr(self, '_fs_poll_timer'):
            self._fs_poll_timer = QTimer(self)
            self._fs_poll_timer.setInterval(400)
            self._fs_poll_timer.timeout.connect(self._poll_fullscreen_state)
        self._fs_poll_timer.start()

        logger.info("Fullscreen ON")

    def _poll_fullscreen_state(self):
        if not self._media_player or not self._is_fullscreen:
            self._stop_fs_poll()
            return
        try:
            if not self._media_player.get_fullscreen():
                self._is_fullscreen = False
                self._stop_fs_poll()
                logger.info("Fullscreen exited (user)")
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
        self._stop_fs_poll()

        if self._media_player:
            try:
                self._media_player.set_fullscreen(False)
            except Exception as e:
                logger.warning(f"VLC set_fullscreen(False): {e}")

        logger.info("Fullscreen OFF")

    def is_fullscreen(self) -> bool:
        """返回当前是否全屏"""
        return self._is_fullscreen'''

new = '''    # ==================================================================
    #  全屏 - Qt native approach
    #  VLC set_fullscreen/toggle_fullscreen are BROKEN when embedded
    #  via set_hwnd. We reparent _player_container into a frameless
    #  top-level QWidget shown fullscreen. _video_widget HWND stays
    #  unchanged - no VLC rebind needed - playback continues.
    # ==================================================================

    def toggle_fullscreen(self):
        if self._is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        if not self._media_player:
            return

        self._is_fullscreen = True
        self._fs_orig_layout = self.layout()
        if self._fs_orig_layout:
            self._fs_orig_layout.removeWidget(self._player_container)

        self._fs_window = QWidget(
            None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self._fs_window.setStyleSheet("background-color: #000;")
        from PyQt6.QtWidgets import QVBoxLayout as _VL
        _fl = _VL(self._fs_window)
        _fl.setContentsMargins(0, 0, 0, 0)
        _fl.addWidget(self._player_container)
        self._player_container.setParent(self._fs_window)
        self._fs_window.keyPressEvent = (
            lambda e: self._exit_fullscreen() if e.key() == Qt.Key.Key_Escape else None
        )
        self._fs_window.showFullScreen()
        logger.info("Fullscreen ON (Qt native)")

    def _exit_fullscreen(self):
        if not self._is_fullscreen:
            return

        was_playing = (self._current_state == "playing")
        saved_pos = self.get_time()
        self.pause()

        if hasattr(self, "_fs_window") and self._fs_window is not None:
            fl = self._fs_window.layout()
            if fl:
                fl.removeWidget(self._player_container)
            self._player_container.setParent(self)
            if self._fs_orig_layout:
                self._fs_orig_layout.addWidget(self._player_container)
            self._fs_window.close()
            self._fs_window.deleteLater()
            self._fs_window = None

        self._is_fullscreen = False

        if was_playing and self._media_player:
            self._media_player.play()
            self._media_player.set_time(int(saved_pos * 1000))
            self._tick_timer.start()
            self._end_check_timer.start()

        logger.info("Fullscreen OFF")

    def is_fullscreen(self) -> bool:
        return self._is_fullscreen'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK: player.py fullscreen replaced")
else:
    print("FAIL: old section not found")
