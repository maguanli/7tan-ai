"""
诊断脚本 — 排查登录后主窗口不弹出的问题
运行: .venv\Scripts\python.exe diag_startup.py
"""
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 50)
print("7Tan 启动诊断")
print("=" * 50)

# 1
print("\n[1/6] QWebEngine...", end=" ", flush=True)
try:
    import PyQt6.QtWebEngineWidgets
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

# 2
print("[2/6] QApplication...", end=" ", flush=True)
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

# 3
print("[3/6] 导入 ui.app...", end=" ", flush=True)
try:
    from ui.app import MainWindow, DARK_STYLESHEET
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)
    print("OK")
except Exception as e:
    traceback.print_exc()
    print(f"FAIL: {e}")
    sys.exit(1)

# 4
print("[4/6] 登录流程...", end=" ", flush=True)
try:
    from ui.login_dialog import show_login_dialog
    from security.token_store import is_token_available, load_token
    
    user_info = None
    if is_token_available():
        data = load_token()
        if data:
            user_info = {"token": data.get("token",""), "username": data.get("username",""),
                         "level": data.get("level","free"), "pro_expires": data.get("pro_expires",0),
                         "pro_license": data.get("pro_license","")}
    
    if user_info is None:
        user_info = show_login_dialog()
    
    if user_info is None:
        print("CANCELLED (用户取消登录)")
        sys.exit(0)
    print(f"OK (用户: {user_info.get('username')})")
except Exception as e:
    traceback.print_exc()
    print(f"FAIL: {e}")
    sys.exit(1)

# 5
print("[5/6] 创建 MainWindow...", end=" ", flush=True)
try:
    window = MainWindow(user_info=user_info)
    print("OK")
except Exception as e:
    traceback.print_exc()
    print(f"FAIL: {e}")
    sys.exit(1)

# 6
print("[6/6] show() + exec()...", flush=True)
try:
    window.show()
    from PyQt6.QtCore import QTimer
    print(">>> 主窗口已显示！3秒后自动关闭...")
    QTimer.singleShot(3000, app.quit)
    app.exec()
    print("DONE — 一切正常")
except Exception as e:
    traceback.print_exc()
    print(f"FAIL: {e}")
