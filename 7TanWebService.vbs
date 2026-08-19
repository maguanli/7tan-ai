Set ws = CreateObject("WScript.Shell")
ws.CurrentDirectory = "D:\7tan\7tanAI"
ws.Run """D:\7tan\7tanAI\.venv\Scripts\pythonw.exe"" ""D:\7tan\7tanAI\main.py"" --web --host 0.0.0.0 --port 9900", 0, False
