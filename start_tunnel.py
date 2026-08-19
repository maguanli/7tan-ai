# -*- coding: utf-8 -*-
"""Cloudflare 快速隧道：启动 + 保活 + 自动记录公网 URL

用法:
    python start_tunnel.py            # 前台运行（含保活循环，断线自动重启）
    python start_tunnel.py --once     # 只启动一次，不保活（兼容旧行为）
    python start_tunnel.py --debug    # debug 日志（cloudflared_debug.log）

特性:
    * 强制 --protocol http2 --region us（国内网络稳定，避开被墙的 QUIC/UDP）
    * 检测进程退出自动重启，新 URL 自动保存到 data/tunnel_url.txt
    * 网页「远程访问」页可读取该文件显示当前公网地址
"""
import subprocess, os, time, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, 'logs', 'cloudflared.log')
DEBUG_LOG = os.path.join(ROOT, 'logs', 'cloudflared_debug.log')
EXE = os.path.join(ROOT, 'tools', 'cloudflared.exe')
URL_FILE = os.path.join(ROOT, 'data', 'tunnel_url.txt')


def ensure_data_dir():
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)


def start_once(debug=False):
    try:
        os.remove(LOG)
    except FileNotFoundError:
        pass
    logf = open(DEBUG_LOG if debug else LOG, 'ab')
    cmd = [EXE, 'tunnel', '--url', 'http://127.0.0.1:9900',
           '--no-autoupdate', '--protocol', 'http2', '--region', 'us']
    if debug:
        cmd += ['--loglevel', 'debug']
    p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return p


def find_url():
    try:
        txt = open(LOG, 'r', encoding='utf-8', errors='ignore').read()
        m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', txt)
        return m.group(0) if m else None
    except Exception:
        return None


def save_url(url):
    ensure_data_dir()
    with open(URL_FILE, 'w', encoding='utf-8') as f:
        f.write(url + '\n')


def wait_url(proc, timeout=45):
    t0 = time.time()
    while time.time() - t0 < timeout:
        url = find_url()
        if url:
            return url
        if proc.poll() is not None:
            print(f'TUNNEL_EXITED rc={proc.returncode}')
            return None
        time.sleep(2)
    return None


def main():
    debug = '--debug' in sys.argv
    once = '--once' in sys.argv
    proc = start_once(debug)
    print('TUNNEL_PID', proc.pid, flush=True)

    url = wait_url(proc)
    if url:
        save_url(url)
        print('TUNNEL_URL', url, flush=True)
    else:
        print('TUNNEL_URL NOT_FOUND', flush=True)
        if proc.poll() is not None:
            return

    if once:
        return

    print('KEEPALIVE ON', flush=True)
    while True:
        time.sleep(5)
        if proc.poll() is not None:
            print(f'{time.strftime("%H:%M:%S")} tunnel exited rc={proc.returncode}, restarting...', flush=True)
            proc = start_once(debug)
            url = wait_url(proc)
            if url:
                save_url(url)
                print('NEW_URL', url, flush=True)


if __name__ == '__main__':
    main()
