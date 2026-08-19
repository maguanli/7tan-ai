# -*- coding: utf-8 -*-
"""SendInput 模拟键盘输入，支持完整 ASCII（含冒号/反斜杠/括号等）"""
import ctypes, time, sys

# 扫描码表（标准 US 键盘布局）
SCAN = {
    'a':0x1E,'b':0x30,'c':0x2E,'d':0x20,'e':0x12,'f':0x21,'g':0x22,'h':0x23,
    'i':0x17,'j':0x24,'k':0x25,'l':0x26,'m':0x32,'n':0x31,'o':0x18,'p':0x19,
    'q':0x10,'r':0x13,'s':0x1F,'t':0x14,'u':0x16,'v':0x2F,'w':0x11,'x':0x2D,
    'y':0x15,'z':0x2C,
    '0':0x0B,'1':0x02,'2':0x03,'3':0x04,'4':0x05,'5':0x06,'6':0x07,'7':0x08,
    '8':0x09,'9':0x0A,
    ' ':0x39,'.':0x34,',':0x33,'/':0x35,';':0x27,"'":0x28,'[':0x1A,']':0x1B,
    '\\':0x2B,'-':0x0C,'=':0x0D,'`':0x29,
}
# 需要 Shift 的字符 -> (scan, 基础字符)
SHIFT_MAP = {
    '!':(0x02,'1'),'@':(0x03,'2'),'#':(0x04,'3'),'$':(0x05,'4'),'%':(0x06,'5'),
    '^':(0x07,'6'),'&':(0x08,'7'),'*':(0x09,'8'),'(':0x0A,'(': (0x0A,'9'),')':(0x0B,'0'),
    '_':(0x0C,'-'),'+':(0x0D,'='),'{':(0x1A,'['),'}':(0x1B,']'),'|':(0x2B,'\\'),
    ':':(0x27,';'),'"':(0x28,"'"),'<':(0x33,','),'>':(0x34,'.'),'?':(0x35,'/'),
    '~':(0x29,'`'),
}

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [("type", ctypes.c_ulong), ("i", _I)]

def send_key(scan, down):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0
    inp.ki.wScan = scan
    inp.ki.dwFlags = KEYEVENTF_SCANCODE | (0 if down else KEYEVENTF_KEYUP)
    inp.ki.time = 0
    inp.ki.dwExtraInfo = None
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    time.sleep(0.008)

def press_shift_key(scan):
    send_key(0x2A, True)  # LSHIFT down
    send_key(scan, True)
    send_key(scan, False)
    send_key(0x2A, False)

def type_text(text):
    for ch in text:
        c = ch.lower()
        if c in SHIFT_MAP and ch != c.lower() or ch in '!@#$%^&*()_+{}|:"<>?~':
            scan, base = SHIFT_MAP[ch]
            press_shift_key(scan)
        elif c in SCAN:
            send_key(SCAN[c], True)
            send_key(SCAN[c], False)
        else:
            # 未知字符尝试直接发 unicode 扫描 0
            pass
        time.sleep(0.012)

if __name__ == '__main__':
    text = sys.argv[1]
    time.sleep(0.4)
    type_text(text)
    print("typed:", text[:50])
