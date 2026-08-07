# -*- coding: utf-8 -*-
"""
图标/图片按钮定位器：不依赖 OCR 文字识别
用 HSV 色块检测 + 矩形轮廓分析，找出屏幕上类似"按钮"的区域
用法: python find_button.py <截图路径> [--debug]
输出: JSON 候选按钮坐标(屏幕坐标) + 颜色 + 尺寸
"""
import sys, json, os

IMG_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/screenshots/habo_full.png"
DEBUG = "--debug" in sys.argv

# ---------- 1. 环境检查 ----------
try:
    import cv2
    import numpy as np
    HAVE_CV = True
except Exception as e:
    HAVE_CV = False
    print(f"[env] cv2/numpy 不可用: {e}")

if not HAVE_CV:
    # 退路：用 PIL 像素扫描
    try:
        from PIL import Image
        HAVE_PIL = True
    except Exception as e:
        HAVE_PIL = False
        print(f"[env] PIL 也不可用: {e}")
else:
    HAVE_PIL = False

# ---------- 2. 检测逻辑 ----------
# 常见按钮色域（HSV，OpenCV 范围 H:0-180 S:0-255 V:0-255）
# 腾讯系社区按钮常见色：蓝(#0a7cf6 ~ h=140) / 红(#fa5151 h=0) / 绿(#07c160 h=85) / 橙(#ff8c00 h=15)
COLOR_RANGES = {
    "blue":   [(95, 80, 80), (130, 255, 255)],
    "red":    [(0, 80, 80), (10, 255, 255)],
    "red2":   [(170, 80, 80), (180, 255, 255)],
    "green":  [(75, 60, 60), (95, 255, 255)],
    "orange": [(10, 80, 80), (25, 255, 255)],
}

def detect_cv(path):
    img = cv2.imread(path)
    if img is None:
        print(json.dumps({"error": f"cannot read {path}"}))
        return
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    results = []
    for name, (lo, hi) in COLOR_RANGES.items():
        mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
        # 形态学闭运算填补按钮内部
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            # 按钮尺寸范围：高 20-200px，宽 40-500px，面积适中
            if ch < 18 or ch > 220 or cw < 40 or cw > 600:
                continue
            if area < 800 or area > 500000:
                continue
            fill = area / (cw * ch)
            if fill < 0.2:  # 太稀疏说明不是实心块
                continue
            cx, cy = x + cw // 2, y + ch // 2
            results.append({
                "color": name, "x": x, "y": y, "w": cw, "h": ch,
                "cx": cx, "cy": cy, "area": area, "fill": round(fill, 2)
            })
    # 按面积降序
    results.sort(key=lambda r: -r["area"])
    print(json.dumps({"size": [w, h], "candidates": results[:30]}, ensure_ascii=False))
    if DEBUG:
        out = path.replace(".png", "_btns.png")
        dbg = img.copy()
        for r in results[:30]:
            cv2.rectangle(dbg, (r["x"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (0, 255, 0), 2)
            cv2.putText(dbg, f"{r['color']} {r['cx']},{r['cy']}", (r["x"], max(12, r["y"]-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imwrite(out, dbg)
        print(f"[debug] 标注图已保存: {out}")

def detect_pil(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    # 简版：统计每行每列的彩色像素密度（饱和度高=彩色）
    from collections import Counter
    # 采样扫描找彩色块
    # 转 HSV（PIL 用 0-255 H）
    def rgb2hsv(r, g, b):
        import colorsys
        hh, ss, vv = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        return hh*180, ss*255, vv*255
    results = []
    # 逐块扫描 8x8 网格统计
    step = 8
    block = Counter()
    for yy in range(0, h, step):
        for xx in range(0, w, step):
            r, g, b = px[xx, yy]
            hh, ss, vv = rgb2hsv(r, g, b)
            if ss > 120 and vv > 80:
                block[(xx//step, yy//step)] = 1
    print(json.dumps({"size": [w, h], "note": "PIL fallback: only density map", "candidates": []}, ensure_ascii=False))

if __name__ == "__main__":
    if not os.path.exists(IMG_PATH):
        print(json.dumps({"error": f"file not found: {IMG_PATH}"}))
        sys.exit(1)
    print(f"[info] 分析: {IMG_PATH}")
    if HAVE_CV:
        detect_cv(IMG_PATH)
    elif HAVE_PIL:
        detect_pil(IMG_PATH)
    else:
        print(json.dumps({"error": "no cv2/PIL, install: pip install opencv-python numpy"}))
