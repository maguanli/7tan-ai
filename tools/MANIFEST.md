# tools/ 入口清单

生成：2026-10-25 16:43

> **状态列只有你能填**：`在用（勿动）` / `待确认` / `可弃`。空白 = 未判定，任何人不得移动该文件。

> **"无证据"不等于"没在用"。** 本清单只做证据归集，不做生死判定。插件按路径 importlib 加载、运行时拼路径 subprocess 调用，静态扫描都看不到。

## 甲、强证据：被 bat 脚本或 src 直接调用（6 个）—— 不要动

| 文件 | 最后修改 | 证据 | 状态 |
|---|---|---|---|
| `sanitize_config_for_build.py` | 2026-08-27 | bat(名): build_and_sync.bat:63, build_and_sync.bat:103, build_and_sync.bat:150 |  |
| `security_src/license_verify.py` | 2026-07-31 | bat(名): build_and_sync.bat:128 |  |
| `security_src/rsa_verify.py` | 2026-07-27 | bat(名): build_and_sync.bat:127 |  |
| `security_src/safe_modify.py` | 2026-07-27 | bat(名): build_and_sync.bat:129 |  |
| `security_src/token_store.py` | 2026-09-13 | bat(名): build_and_sync.bat:132 |  |
| `web_autostart.py` | 2026-09-13 | bat(名): 启动网页版服务(Windows).bat:30, 启动网页版服务(Windows).bat:33, 启动网页版服务(Windows).bat:50 ; src: src\web\server.py:786, src\web\server.py:787 |  |

## 乙、中证据：含动态加载特征（103 个）—— 仅标记

含 `importlib` / `runpy` / `subprocess` / `__main__`，可能被插件系统或运行时调用。

| 文件 | 最后修改 | 特征 | 状态 |
|---|---|---|---|
| `check_integrity.py` | 2026-08-14 | dyn: __main__ |  |
| `gen_plugin_guard.py` | 2026-08-03 | dyn: __main__ |  |
| `gen_plugin_hashes.py` | 2026-08-03 | dyn: __main__ |  |
| `gzh_publish/analyze_dialog_colors.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/analyze_dialog_full.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/analyze_dialog_zoom.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/check_cdp.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/check_cover.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_bottom_publish.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_browser_tab.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_cover.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_final_confirm.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_green_confirm.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_original_switch.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_preview_test.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_publish2.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_publish_btn.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_qunfa.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_timing.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/click_upload_btn.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/confirm_original.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/confirm_publish.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/dialog_select_original.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/esc_close_dialog.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fill_digest.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fill_digest2.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fill_digest3.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fill_digest4.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fill_digest5.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fill_digest6.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fill_title_author.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_bottom_buttons.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_button_blocks.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_button_color.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_button_zone.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_buttons.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_chars.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_digest_count.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_digest_hint.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_final_btn.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_green_button.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_ok_button.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_qrcode.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_upload_btn.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_xy.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/find_xy2.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fix_digest_final.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/fix_title_author.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/focus_and_click_tab.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/full_ocr_state.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/get_window_rect.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/local_ocr.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/locate_draft.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/locate_green_btn.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/minimize_and_switch.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_bottom_wide.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_browser_area.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_crop_zone.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_dialog.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_dialog_bottom.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_dialog_bottom2.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_dialog_buttons.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_dialog_zone3.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_dialog_zoom.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_editor_area.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_editor_regions.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_editor_rightcol.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_editor_words.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_enhanced_dialog.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_full_zone.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_image.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_left_col2.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_original_row.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_right_panel.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_settings_panel.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_settings_words.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_summary_zone.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_timing_enhanced.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_timing_panel.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_top_words.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_verify_dialog.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/ocr_zone2.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/paste_body.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/press_enter_publish.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/press_esc.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/probe_digest.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/recover_editor3.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/sample_publish_btn.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/save_draft2.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/save_draft3.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/scroll_editor.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/sendinput_click_publish.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/switch_to_browser_tab.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/test_dpi.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/test_resolve.py` | 2026-08-08 | dyn: importlib |  |
| `gzh_publish/typewrite_digest.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/undo_and_find_digest.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/verify_editor.py` | 2026-08-08 | dyn: __main__ |  |
| `gzh_publish/verify_editor_right.py` | 2026-08-08 | dyn: __main__ |  |
| `platform_adapter.py` | 2026-08-15 | dyn: importlib |  |
| `security_src/plugin_guard.py` | 2026-08-03 | dyn: importlib |  |
| `startup_test.py` | 2026-08-05 | dyn: importlib |  |
| `wechat_click.py` | 2026-08-08 | dyn: __main__ |  |

## 丙、无证据：静态扫描无任何入口（126 个）—— 原地不动，等你判定

| 文件 | 最后修改 | 状态 |
|---|---|---|
| `adaptive_flow.py` | 2026-08-08 |  |
| `analyze_shot.py` | 2026-08-08 |  |
| `article_v2.py` | 2026-08-08 |  |
| `article_v3.py` | 2026-08-08 |  |
| `article_v4.py` | 2026-08-08 |  |
| `back_list.py` | 2026-08-08 |  |
| `build.py` | 2026-08-01 |  |
| `camera_vision/camera_do.py` | 2026-08-09 |  |
| `capture_login.py` | 2026-08-01 |  |
| `check_img.py` | 2026-08-08 |  |
| `check_popup.py` | 2026-08-08 |  |
| `check_pyd_symbols.py` | 2026-08-03 |  |
| `click_article.py` | 2026-08-08 |  |
| `click_hot.py` | 2026-08-08 |  |
| `click_hot2.py` | 2026-08-08 |  |
| `click_hot_v4.py` | 2026-08-08 |  |
| `click_left.py` | 2026-08-08 |  |
| `compile_harden.py` | 2026-08-03 |  |
| `convert_wechat_v5.py` | 2026-08-27 |  |
| `crop_qrcode.py` | 2026-08-08 |  |
| `current_view.py` | 2026-08-08 |  |
| `design_sidebar_icons.py` | 2026-08-02 |  |
| `desktop_bot/desktop_do.py` | 2026-08-27 |  |
| `diag.py` | 2026-08-08 |  |
| `diag2.py` | 2026-08-08 |  |
| `do_search.py` | 2026-08-08 |  |
| `encrypt_strings.py` | 2026-08-27 |  |
| `exit_article.py` | 2026-08-08 |  |
| `exit_page.py` | 2026-08-08 |  |
| `explore_left.py` | 2026-08-08 |  |
| `explore_top.py` | 2026-08-08 |  |
| `final_attempt.py` | 2026-08-08 |  |
| `find_button.py` | 2026-08-08 |  |
| `find_cookies.py` | 2026-08-08 |  |
| `find_hot_now.py` | 2026-08-08 |  |
| `find_new_wx.py` | 2026-08-08 |  |
| `find_search.py` | 2026-08-08 |  |
| `find_suggest.py` | 2026-08-08 |  |
| `fix_env_paths.py` | 2026-08-20 |  |
| `fix_novel_plugin_reg.py` | 2026-08-10 |  |
| `flow3.py` | 2026-08-08 |  |
| `flow_final.py` | 2026-08-08 |  |
| `flow_v6.py` | 2026-08-08 |  |
| `flow_v7.py` | 2026-08-08 |  |
| `full_flow.py` | 2026-08-08 |  |
| `gen_sec_config.py` | 2026-08-27 |  |
| `get_gzh_draft.py` | 2026-08-08 |  |
| `gzh_publish/_setup.py` | 2026-08-08 |  |
| `gzh_publish/cards_gen.py` | 2026-08-08 |  |
| `gzh_publish/dump_layout.py` | 2026-08-08 |  |
| `gzh_publish/gzh_do.py` | 2026-08-08 |  |
| `gzh_publish/list_windows.py` | 2026-08-08 |  |
| `gzh_publish/ocr_locate_click.py` | 2026-08-08 |  |
| `gzh_publish/paste_cards.py` | 2026-08-08 |  |
| `gzh_publish/recover_editor.py` | 2026-08-08 |  |
| `gzh_publish/recover_editor2.py` | 2026-08-08 |  |
| `gzh_publish/region_ocr.py` | 2026-08-09 |  |
| `gzh_publish/save_draft.py` | 2026-08-08 |  |
| `gzh_publish/set_cover.py` | 2026-08-08 |  |
| `gzh_publish/set_cover2.py` | 2026-08-08 |  |
| `gzh_publish/verify_cards.py` | 2026-08-08 |  |
| `gzh_publish/verify_tail.py` | 2026-08-08 |  |
| `list_data.py` | 2026-08-08 |  |
| `list_windows.py` | 2026-08-08 |  |
| `locate_hot.py` | 2026-08-08 |  |
| `max_wx.py` | 2026-08-08 |  |
| `ocr_attrs.py` | 2026-08-08 |  |
| `ocr_compare.py` | 2026-08-08 |  |
| `ocr_debug.py` | 2026-08-08 |  |
| `ocr_full_page.py` | 2026-08-08 |  |
| `ocr_locate_click.py` | 2026-08-08 |  |
| `ocr_selftest.py` | 2026-08-08 |  |
| `open_article.py` | 2026-08-08 |  |
| `open_article2.py` | 2026-08-08 |  |
| `open_news_article.py` | 2026-08-08 |  |
| `open_panel.py` | 2026-08-08 |  |
| `open_search2.py` | 2026-08-08 |  |
| `p0_fix_release.py` | 2026-08-03 |  |
| `p0_fix_release_final.py` | 2026-08-03 |  |
| `p0_fix_release_final2.py` | 2026-08-03 |  |
| `p0_fix_release_final3.py` | 2026-08-03 |  |
| `probe2.py` | 2026-08-08 |  |
| `probe_cdp.py` | 2026-08-08 |  |
| `probe_list_top.py` | 2026-08-08 |  |
| `probe_search.py` | 2026-08-08 |  |
| `read_article_full.py` | 2026-08-08 |  |
| `region_ocr.py` | 2026-08-09 |  |
| `register_sunzi.py` | 2026-08-08 |  |
| `restore_wechat.py` | 2026-08-08 |  |
| `retry_search.py` | 2026-08-08 |  |
| `retry_sousou.py` | 2026-08-08 |  |
| `scan_hj.py` | 2026-10-17 |  |
| `scan_hj2.py` | 2026-10-17 |  |
| `scan_hj3.py` | 2026-10-17 |  |
| `scan_hj4.py` | 2026-10-17 |  |
| `scroll_hot.py` | 2026-08-08 |  |
| `scroll_hot2.py` | 2026-08-08 |  |
| `security_src/auth_client_src.py` | 2026-08-27 |  |
| `security_src/device_fingerprint.py` | 2026-08-01 |  |
| `security_src/entry_auth.py` | 2026-08-02 |  |
| `security_src/prompts.py` | 2026-08-02 |  |
| `security_src/sec_config.py` | 2026-08-02 |  |
| `security_src/updater.py` | 2026-08-02 |  |
| `sousou_home.py` | 2026-08-08 |  |
| `stable_flow.py` | 2026-08-08 |  |
| `tmp_check_prefs.py` | 2026-08-27 |  |
| `tmp_find_logs.py` | 2026-08-27 |  |
| `tmp_grep_wizard.py` | 2026-08-27 |  |
| `tmp_inspect_zip.py` | 2026-08-27 |  |
| `tmp_poll.py` | 2026-08-27 |  |
| `tmp_read_logs.py` | 2026-08-27 |  |
| `tmp_scan_login.py` | 2026-08-27 |  |
| `tmp_scan_voice.py` | 2026-08-27 |  |
| `tmp_tail.py` | 2026-08-27 |  |
| `topmost_wx.py` | 2026-08-08 |  |
| `uia_dump.py` | 2026-08-08 |  |
| `verify_gzh.py` | 2026-08-08 |  |
| `verify_input.py` | 2026-08-08 |  |
| `verify_novel_plugin.py` | 2026-08-10 |  |
| `verify_release_zip.py` | 2026-08-08 |  |
| `verify_sunzi.py` | 2026-08-08 |  |
| `viral_writer/tools.py` | 2026-10-06 |  |
| `watch_login.py` | 2026-08-01 |  |
| `wechat_helper.py` | 2026-08-08 |  |
| `wechat_scan.py` | 2026-08-08 |  |
| `zoom_top.py` | 2026-08-08 |  |

## 丁、计划任务命中

- `"\7Tan Bridge Autostart","N/A","就绪"`
- `"\7tan_upload_free","N/A","就绪"`
- `"\DSH-AutoStart","N/A","就绪"`

## 附：扫描口径

- 扫了根目录 / `scripts/` / `tools/` 下 38 个 `.bat`，提取 python 调用行
- 扫了 `src/` `webmirror/` 对 `tools.xxx` 的 import
- 未扫 `downloads/`（一次性任务脚本，不进产品包）
- 计划任务查询可能因权限返回空，空结果不能证明"没有计划任务"
