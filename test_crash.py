"""Test code_viewer crash"""
import sys, traceback
sys.path.insert(0, '.')

# Test 1: Import
try:
    from src.ui.code_viewer import CodeEditor, CodeViewer
    print("Test 1 PASS: Import OK")
except Exception as e:
    print(f"Test 1 FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 2: Create CodeEditor (no QApplication needed for basic creation)
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    editor = CodeEditor()
    editor.setPlainText("line 1\nline 2\nline 3")
    print("Test 2 PASS: CodeEditor created")
except Exception as e:
    print(f"Test 2 FAIL: {e}")
    traceback.print_exc()

# Test 3: _highlight_current_line
try:
    editor._highlight_current_line()
    print("Test 3 PASS: _highlight_current_line")
except Exception as e:
    print(f"Test 3 FAIL: {e}")
    traceback.print_exc()

# Test 4: _highlight_line
try:
    editor._highlight_line(1)
    print("Test 4 PASS: _highlight_line")
except Exception as e:
    print(f"Test 4 FAIL: {e}")
    traceback.print_exc()

# Test 5: Full CodeViewer
try:
    viewer = CodeViewer()
    print("Test 5 PASS: CodeViewer created")
except Exception as e:
    print(f"Test 5 FAIL: {e}")
    traceback.print_exc()

print("\nAll tests done.")
app.quit()
