# -*- coding: utf-8 -*-
import ctypes
from ctypes import wintypes

CCH_RM_MAX_APP_NAME = 255
CCH_RM_MAX_SVC_NAME = 63

class RM_UNIQUE_PROCESS(ctypes.Structure):
    _fields_ = [("dwProcessId", wintypes.DWORD),
                ("ProcessStartTime", wintypes.FILETIME)]

class RM_PROCESS_INFO(ctypes.Structure):
    _fields_ = [
        ("Process", RM_UNIQUE_PROCESS),
        ("strAppName", ctypes.c_wchar * CCH_RM_MAX_APP_NAME),
        ("strServiceShortName", ctypes.c_wchar * CCH_RM_MAX_SVC_NAME),
        ("ApplicationType", ctypes.c_uint),
        ("AppStatus", ctypes.c_uint),
        ("TSSessionId", ctypes.c_uint),
        ("bRestartable", ctypes.c_int),
    ]

path = r"D:\用户目录\下载\新建文件夹 123\recording_20260814_030943.mkv"

rstrtmgr = ctypes.windll.rstrtmgr
session = wintypes.DWORD()
rstrtmgr.RmStartSession(ctypes.byref(session), 0, None)

files = (ctypes.c_wchar_p * 1)(path)
rstrtmgr.RmRegisterResources(session, 1, files, 0, None, 0, None)

nProcInfoNeeded = wintypes.DWORD()
nProcInfo = wintypes.DWORD(20)
rg = (RM_PROCESS_INFO * 20)()
reason = wintypes.DWORD(0)

rc = rstrtmgr.RmGetList(session, ctypes.byref(nProcInfoNeeded),
                        ctypes.byref(nProcInfo), rg, ctypes.byref(reason))
print("RmGetList rc =", rc, "needed =", nProcInfoNeeded.value, "proc =", nProcInfo.value)

for i in range(min(nProcInfo.value, 20)):
    info = rg[i]
    print("PID:", info.Process.dwProcessId, "| App:", info.strAppName, "| Type:", info.ApplicationType)

rstrtmgr.RmEndSession(session)
