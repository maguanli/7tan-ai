#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       7坛AI小编 v5.1.0              ║"
echo "║  自动抓取-改写-发布 绿色免安装      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "══════════════════════════════════════"
    echo " [检测] 未找到 Python3 运行环境"
    echo "══════════════════════════════════════"
    echo ""
    echo " 请先安装 Python 3.11+:"
    echo "   Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "   CentOS/RHEL:   sudo yum install python3"
    echo "   macOS:         brew install python@3.12"
    echo ""
    exit 1
fi

# 虚拟环境
if [ ! -f ".venv/bin/python3" ]; then
    echo "[信息] 创建虚拟环境..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Playwright
python3 -c "from playwright.sync_api import sync_playwright; sync_playwright().start().chromium.launch(); print('OK')" &>/dev/null
if [ $? -ne 0 ]; then
    echo "[信息] 首次运行，安装 Playwright Chromium..."
    playwright install chromium
fi

echo "[启动] 7坛AI小编..."
python3 main.py "$@"
