# -*- coding: utf-8 -*-
"""临时静态文件服务器：为本地 HTML 预览提供 http 访问"""
import os
import http.server
import socketserver

TARGET_DIR = r"D:\用户目录\下载\新建文件夹 123\花朵上的小蝴蝶"
PORT = 8123

os.chdir(TARGET_DIR)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    httpd.serve_forever()
