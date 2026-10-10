import os, glob, shutil
d = r'D:\7tan\dsh-workspace\chun-guo-rizi'
os.chdir(d)
htmls = sorted(glob.glob('*.html'), key=lambda f: os.path.getsize(f), reverse=True)
print('htmls by size:', [(f, os.path.getsize(f)) for f in htmls])
src = htmls[0]
dst = '_gzh_paste.html'
shutil.copy(src, dst)
print('copied ->', os.path.abspath(dst), os.path.getsize(dst))
os.startfile(os.path.abspath(dst))
print('OPENED_OK')
