# -*- coding: utf-8 -*-
"""用 pyperclip 写剪贴板"""
import sys
try:
    import pyperclip
except ImportError:
    print('NO_PYPERCLIP')
    sys.exit(1)

text = ("7Tan Editor is a legitimate AI desktop assistant tool developed by an "
        "individual developer. It is a PyInstaller-packaged Python application. "
        "The software was falsely detected as PUA (potentially unwanted app). "
        "It contains no malicious behavior: no keylogging, no self-startup, "
        "no registry modification, no silent elevation. Please review and "
        "remove the false positive detection. Thank you.")

pyperclip.copy(text)
print('CLIP_OK len=', len(text))
