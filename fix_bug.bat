@echo off
cd /d D:\7tan\7tanAI
python -c "content=open('src/tools/browser_tools.py','r',encoding='utf-8').read();content=content.replace('if _web_view is not None:','if _get_active_view() is not None:').replace('if _web_view is None:','if _get_active_view() is None:');open('src/tools/browser_tools.py','w',encoding='utf-8').write(content);print('OK')"
