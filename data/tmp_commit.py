# -*- coding: utf-8 -*-
import sys, io, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
repo = r'D:\7tan\7tanAI'

def git(*args):
    r = subprocess.run(['git'] + list(args), cwd=repo, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout.strip(), r.stderr.strip()

rc, out, err = git('add', '-A')
print('ADD:', rc, out or err)
rc, out, err = git('commit', '-m', 'chore(build): rebuild dist and package v1.0.6 release zips')
print('COMMIT:', rc, out or err)
rc, out, err = git('log', '--oneline', '-2')
print('LOG:', out)
