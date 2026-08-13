# -*- coding: utf-8 -*-
"""输入 Additional information 英文说明"""
import time
import pyautogui

text = ("7Tan Editor is a legitimate AI desktop assistant tool developed by an "
        "individual developer. It is a PyInstaller-packaged Python application. "
        "The software was falsely detected as PUA (potentially unwanted app). "
        "It contains no malicious behavior: no keylogging, no self-startup, "
        "no registry modification, no silent elevation. Please review and "
        "remove the false positive detection. Thank you.")

time.sleep(0.5)
pyautogui.write(text, interval=0.005)
time.sleep(0.3)
print('TYPED additional info, len=', len(text))
