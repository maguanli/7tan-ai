# -*- coding: utf-8 -*-
"""
CogVideoX-3 视频去「AI生成」水印工具 v2.0
方法：裁剪法（替代v1的delogo修补法）
  - delogo会在原水印处留下光滑模糊斑，人眼在播放时可见
  - 裁剪法直接切掉底部水印区，再等比放大回原分辨率，零痕迹零变形
用法：python remove_ai_watermark_v2.py 输入.mp4 输出.mp4 [裁剪高度，默认130]
适用：1080x1920 竖屏输出（水印位于 y>=1800）
"""
import subprocess
import sys


def remove_watermark(src: str, dst: str, cut_h: int = 130):
    # 1080x1920 -> 裁掉底部cut_h -> 等比放大回高1920 -> 居中裁回宽1080
    w, h = 1080, 1920
    kept = h - cut_h                      # 1790
    scaled_w = round(w * h / kept / 2) * 2  # 1158 (偶数)
    x_off = (scaled_w - w) // 2             # 39
    vf = (
        f'crop={w}:{kept}:0:0,'
        f'scale={scaled_w}:{h}:flags=lanczos,'
        f'crop={w}:{h}:{x_off}:0'
    )
    cmd = ['ffmpeg', '-y', '-i', src, '-vf', vf,
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
           '-pix_fmt', 'yuv420p', dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        return False
    print(f'OK: {dst}')
    return True


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cut = int(sys.argv[3]) if len(sys.argv) > 3 else 130
    remove_watermark(sys.argv[1], sys.argv[2], cut)
