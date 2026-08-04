import shutil, os
src = r'D:\7tan\iching-android\app\build\outputs\apk\debug\app-debug.apk'
dst = r'D:\7tan\iching-android\iching-v0.11.0-taiji-ttsfix.apk'
shutil.copy(src, dst)
print('copied ->', dst, os.path.getsize(dst) / 1024 / 1024, 'MB')
