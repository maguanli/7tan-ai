' 通过 WMI 启动 dsh Web 服务（脱离当前进程树，独立存活）
Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set objProcess = objWMIService.Get("Win32_Process")
errReturn = objProcess.Create("G:\nodejs\node.exe node_modules\@deepseek-ai\dsh\lib\bin.js web", "G:\nodejs", null, intProcessID)
WScript.Echo "PID=" & intProcessID & " err=" & errReturn
