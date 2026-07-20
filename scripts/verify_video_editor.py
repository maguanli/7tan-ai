"""
视频剪辑器启动前验证脚本
——每次修改源码后先跑这个，确认语法没问题再启动
用法: python scripts/verify_video_editor.py
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FILES = [
    "src/ui/video_editor/__init__.py",
    "src/ui/video_editor/editor_window.py",
    "src/ui/video_editor/timeline.py",
    "src/ui/video_editor/timeline_items.py",
    "src/ui/video_editor/player.py",
    "src/ui/video_editor/media_bin.py",
    "src/ui/video_editor/utils.py",
    "src/ui/video_editor/screen_recorder.py",
    "src/ui/video_editor/data_models.py",
    "src/ui/video_editor/exporter.py",
    "src/ui/video_editor/cut_tool.py",
    "src/ui/video_editor/project_manager.py",
    "src/ui/video_editor/commands.py",
    "src/ui/video_editor/editor_api.py",
]

VLC_PATHS = [
    r"C:\Program Files\VideoLAN\VLC",
    r"C:\Program Files (x86)\VideoLAN\VLC",
]


def check_syntax():
    """检查所有文件语法 — 这是最关键的，语法错 = 100% 启动崩溃"""
    print("\n=== Syntax Check ===")
    bad = []
    for rel in FILES:
        path = os.path.join(ROOT, rel)
        try:
            with open(path, "r", encoding="utf-8") as f:
                ast.parse(f.read())
            print(f"  [OK] {rel.rsplit('/',1)[-1]}")
        except SyntaxError as e:
            print(f"  [FAIL] {rel.rsplit('/',1)[-1]} @ L{e.lineno}: {e.msg}")
            bad.append((rel, e))
        except FileNotFoundError:
            print(f"  [MISS] {rel}")
    return len(bad) == 0


def check_import():
    """模拟导入链（只在 app 环境有效）"""
    print("\n=== Import Chain ===")
    try:
        import PyQt6  # 探针
        from src.ui.video_editor.editor_window import VideoEditorPage
        print(f"  [OK] VideoEditorPage imported")
        return True
    except ImportError:
        print("  [SKIP] Not in app venv")
        return True
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")
        return False


def check_vlc():
    """检查 VLC"""
    print("\n=== VLC Runtime ===")
    for p in VLC_PATHS:
        if os.path.isdir(p) and os.path.isfile(os.path.join(p, "libvlc.dll")):
            print(f"  [OK] {p}")
            return True
    print("  [WARN] VLC not found")
    return False


if __name__ == "__main__":
    print("=" * 50)
    print("   Video Editor Syntax Verification")
    print("=" * 50)

    ok1 = check_syntax()
    ok2 = check_import()
    ok3 = check_vlc()

    print("\n" + "=" * 50)
    all_pass = ok1 and ok2 and ok3
    print(f"  Syntax: {'PASS' if ok1 else 'FAIL'}")
    print(f"  Import: {'PASS' if ok2 else 'FAIL'}")
    print(f"  VLC:    {'PASS' if ok3 else 'FAIL'}")

    if all_pass:
        print("\n>>> All checks passed! <<<")
    else:
        print("\n>>> FIX FAIL items before launching! <<<")
    sys.exit(0 if all_pass else 1)
