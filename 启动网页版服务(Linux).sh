#!/usr/bin/env bash
# ============================================================
# 7Tan WEB 版启动器（Linux）
# 解压后执行本脚本 → 自动安装依赖 → 启动 9900 WEB 服务 → 打开浏览器
# 用法:  ./Linux-启动网页版服务.sh   或   bash Linux-启动网页版服务.sh
# ============================================================
cd "$(dirname "$0")" || exit 1
mkdir -p logs

echo "=============================================="
echo "  7Tan WEB 版启动器 (Linux)"
echo "=============================================="

# [1/4] 检测系统
UNAME=$(uname -s)
if [ "$UNAME" != "Linux" ]; then
  echo "❌ 本脚本仅支持 Linux；macOS 请双击「macOS-启动网页版服务.command」"
  read -r -p "按回车退出..." _
  exit 1
fi
echo "[1/4] ✅ 检测系统: Linux ($(uname -m))"

# [2/4] 检测 Python3
PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "❌ 未检测到 Python3，请先安装："
  echo "   Debian/Ubuntu: sudo apt install python3 python3-pip python3-venv"
  echo "   Fedora:         sudo dnf install python3 python3-pip"
  echo "   Arch:           sudo pacman -S python python-pip"
  read -r -p "安装完成后重新运行本脚本。按回车退出..." _
  exit 1
fi
echo "[2/4] ✅ Python: $("$PY" --version)"

# [3/4] 检查并安装依赖（首次运行自动安装）
echo "[3/4] 检查依赖..."
if ! "$PY" -c "import fastapi, uvicorn, dotenv, loguru" >/dev/null 2>&1; then
  echo "  → 首次运行，正在安装 WEB 版依赖（可能需要几分钟，请保持网络畅通）..."
  "$PY" -m pip install --upgrade pip -q || true
  if [ -f requirements-web.txt ]; then
    "$PY" -m pip install -r requirements-web.txt -q || {
      echo "❌ 依赖安装失败，请检查网络后重试。"
      read -r -p "按回车退出..." _
      exit 1
    }
  else
    "$PY" -m pip install fastapi uvicorn python-dotenv loguru -q || {
      echo "❌ 依赖安装失败，请检查网络后重试。"
      read -r -p "按回车退出..." _
      exit 1
    }
  fi
fi

# [4/4] 启动 WEB 服务并打开浏览器
echo "[4/4] 启动 7Tan WEB 服务 (http://127.0.0.1:9900/) ..."
if ! "$PY" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',9900))==0 else 1)" >/dev/null 2>&1; then
  if [ -f web_main.py ]; then
    nohup "$PY" web_main.py --host 0.0.0.0 --port 9900 >> logs/web_9900.log 2>&1 &
  else
    nohup "$PY" main.py --web --host 0.0.0.0 --port 9900 >> logs/web_9900.log 2>&1 &
  fi
  echo "  → 服务已后台启动 (PID $!)"
fi

# 等待端口就绪（最多 60 秒）
echo "  → 等待服务就绪..."
for _ in $(seq 1 60); do
  if "$PY" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',9900))==0 else 1)" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# 打开浏览器
(xdg-open "http://127.0.0.1:9900/" >/dev/null 2>&1 || true)

echo ""
echo "✅ 7Tan WEB 版已启动！"
echo "   浏览器已打开: http://127.0.0.1:9900/"
echo "   服务日志: logs/web_9900.log"
echo "   停止服务: pkill -f 'web_main.py'  (或 pkill -f 'main.py --web')"
echo ""
