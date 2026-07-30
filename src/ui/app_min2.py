"""最小测试版 app.py"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel

DARK_STYLESHEET = "QWidget { background: #1e1e1e; }"

class MainWindow(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        self.setWindowTitle("7Tan MIN")
        self.setGeometry(100, 100, 800, 600)
        label = QLabel(f"Hello {user_info.get('username', 'world') if user_info else 'world'}")
        self.setCentralWidget(label)
