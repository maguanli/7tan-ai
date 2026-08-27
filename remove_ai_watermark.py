# -*- coding: utf-8 -*-
"""
CogVideoX-3 输出视频去「AI生成」水印工具（可复用）
用法: python remove_ai_watermark.py <输入.mp4> <输出.mp4>
说明: 智谱官方API强制加水印且无关闭参数；本工具用 delogo 滤镜修复。
      水印位置经三帧交叉验证固定为 x=829~1023, y=1820~1881 (1080x1920)，
      已加padding。其他分辨率需先重新定位。
"""
import sys
import subprocess

# 水印边界框（1080x1920，含安全边距）
WM = dict(x=818, y=1810, w=218, h=84)

def remove_watermark(src: str, dst: str):
    vf = f"delogo=x={WM['x']}:y={WM['y']}:w={WM['w']}:h={WM['h']}"
    r = subprocess.run([
        "ffmpeg", "-y", "-i", src, "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy", dst
    ], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-1000:])
        raise SystemExit(1)
    print(f"完成: {dst}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    remove_watermark(sys.argv[1], sys.argv[2])
