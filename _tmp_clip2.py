import tkinter as tk
try:
    r = tk.Tk(); r.withdraw()
    t = r.clipboard_get()
    print('TK_TEXT_LEN:', len(t))
    print('TK_HEAD:', t[:100].replace('\n', '\\n'))
    r.destroy()
except Exception as e:
    print('TK_ERR:', e)
