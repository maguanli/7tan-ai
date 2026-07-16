@echo off
cd /d D:\7tan\7tanAI
echo Checking syntax of modified files...
"C:\Program Files\Python312\python.exe" -c "import ast; ast.parse(open(r'src\tools\file_tools.py').read()); print('file_tools.py: OK')"
"C:\Program Files\Python312\python.exe" -c "import ast; ast.parse(open(r'src\tools\self_modify_tools.py').read()); print('self_modify_tools.py: OK')"
echo Done.
