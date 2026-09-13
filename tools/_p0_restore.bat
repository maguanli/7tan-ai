@echo off
setlocal
echo ==== [1/6] Restore _python\Lib (stdlib from Python312) ====
robocopy "C:\Program Files\Python312\Lib" "D:\7tan\7tanAI\dist\_python\Lib" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2
echo ==== [2/6] Restore _python\Lib\site-packages (MIR from .venv) ====
robocopy "D:\7tan\7tanAI\.venv\Lib\site-packages" "D:\7tan\7tanAI\dist\_python\Lib\site-packages" /MIR /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2
echo ==== [3/6] Restore _build\src ====
robocopy "D:\7tan\7tanAI\src" "D:\7tan\7tanAI\dist\_build\src" /E /XD _source_backup __pycache__ .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2
echo ==== [4/6] Restore _build\config + data + main.py ====
robocopy "D:\7tan\7tanAI\config" "D:\7tan\7tanAI\dist\_build\config" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2
robocopy "D:\7tan\7tanAI\data" "D:\7tan\7tanAI\dist\_build\data" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2
copy /Y "D:\7tan\7tanAI\main.py" "D:\7tan\7tanAI\dist\_build\main.py" >nul
echo ==== [5/6] Restore tzdata Broken_Hill in _internal ====
if exist "D:\7tan\7tanAI\.venv\Lib\site-packages\tzdata\zoneinfo\Australia\Broken_Hill" (
  copy /Y "D:\7tan\7tanAI\.venv\Lib\site-packages\tzdata\zoneinfo\Australia\Broken_Hill" "D:\7tan\7tanAI\dist\7tan-editor\_internal\tzdata\zoneinfo\Australia\Broken_Hill" >nul
  echo   OK
) else (
  echo   skip - source missing
)
echo ==== [6/6] Verify restored ====
python -c "from pathlib import Path; fs=[r'D:\7tan\7tanAI\dist\_python\Lib\site-packages\aiohttp\test_utils.py',r'D:\7tan\7tanAI\dist\_python\Lib\site-packages\pytest\__init__.py',r'D:\7tan\7tanAI\dist\_python\Lib\site-packages\Crypto\SelfTest\Cipher\test_AES.py',r'D:\7tan\7tanAI\dist\_python\Lib\idlelib\idle_test\test_autocomplete.py',r'D:\7tan\7tanAI\dist\7tan-editor\_internal\tzdata\zoneinfo\Australia\Broken_Hill',r'D:\7tan\7tanAI\dist\_build\src\agent\model_manager.py',r'D:\7tan\7tanAI\dist\_build\main.py']; [print('EXISTS' if Path(f).exists() else 'MISSING', f) for f in fs]"
echo ==== DONE ====
