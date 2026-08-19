# desktop_bot 平台变体说明

本插件为 Windows 专属（pywinauto / winrt / win32gui 深度绑定）。
macOS / Linux 用户首次打开 7Tan WEB 版时，点击【确认适配】后，
适配器会自动把对应平台的变体复制到插件目录并安装依赖。

## 目录结构

```
desktop_bot/
├── tools.py                    # Windows 版（原版，仅 Windows 使用）
└── variants/
    ├── darwin/                 # macOS 变体
    │   ├── tools.py            #   macOS 实现（mss + pyautogui + pytesseract）
    │   ├── requirements-darwin.txt
    │   └── README.md
    ├── linux/                  # Linux（含鸿蒙PC Linux生态）变体
    │   ├── tools.py
    │   ├── requirements-linux.txt
    │   └── README.md
    └── backup/                 # 复制变体时自动备份被覆盖的原文件（适配器生成）
```

## 变体功能范围（macOS / Linux 版）

| 工具 | 可用性 | 说明 |
|------|--------|------|
| desktop_env_check | ✅ | 检查 mss/PIL/pyautogui/pytesseract/系统工具 |
| desktop_windows | ✅ | mac: AppleScript；linux: wmctrl |
| desktop_activate | ✅ | 激活窗口 |
| desktop_screenshot | ✅ | mss 全屏/区域截图 |
| desktop_ocr | ✅ | pytesseract（需系统装 tesseract + 中文包）|
| desktop_click_pos | ✅ | pyautogui 点击 |
| desktop_click_text | ✅ | OCR 定位后点击 |
| desktop_type_text | ✅ | 文本输入 |
| desktop_hotkey | ✅ | 组合键 |
| desktop_verify | ✅ | 文字出现验证 |
| desktop_paste_image | ✅ | 写入系统剪贴板（mac: pbcopy/osascript；linux: xclip）|
| desktop_send_chat | ✅ | 基础聊天发送流程 |
| desktop_uia | ⚠️ | 不可用（pywinauto 仅 Windows），返回提示 |
| desktop_tmatch | ✅ | 需 opencv-python（requirements 已含）|
| desktop_snapshot / desktop_see | ✅ | 窗口 + OCR 基础版 |

## 注意事项

1. macOS 需在「系统设置 → 隐私与安全性 → 辅助功能」授予终端/7Tan 控制权限
2. Linux 需 X11 会话（Wayland 下 pyautogui/wmctrl 受限）
3. Linux 系统工具安装：`sudo apt install xdotool wmctrl xclip tesseract-ocr tesseract-ocr-chi-sim`
4. macOS 系统工具安装：`brew install tesseract`（含语言包 `tesseract-lang`）
