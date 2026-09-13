# -*- coding: utf-8 -*-
"""
camera_do.py — 摄像头视觉后端（camera_vision 插件）
"机器人的眼睛"：摄像头采集 + 视觉大模型（GLM-4V）理解世界

用法:
    python camera_do.py list                          # 枚举摄像头
    python camera_do.py capture --save out.jpg        # 拍照
    python camera_do.py see --save out.jpg            # 拍照 + VLM 理解
    python camera_do.py analyze --image xxx.png       # 分析任意图片
    python camera_do.py watch --seconds 30 --interval 5  # 连续监控

依赖: opencv-python (cv2), requests
视觉模型: 智谱 GLM-4V（config.yaml -> ai.vision，API Key 从 .env 读取）
"""
import sys
import os
import io
import json
import time
import base64
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')

try:
    import cv2
except ImportError:
    cv2 = None


# ============================================================
# 配置读取
# ============================================================
def _load_vision_config():
    """读取视觉大模型配置（.env -> config.yaml -> 默认值）"""
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    api_key = os.environ.get('VISION_API_KEY', '')
    base_url = os.environ.get('VISION_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
    model = os.environ.get('VISION_MODEL', 'glm-4.6V')
    # 兜底：从 config.yaml 读
    if not api_key:
        try:
            import yaml
            cfg = yaml.safe_load((ROOT / 'config' / 'config.yaml').read_text(encoding='utf-8'))
            api_key = cfg.get('ai', {}).get('vision', {}).get('api_key', '')
            base_url = cfg.get('ai', {}).get('vision', {}).get('base_url', base_url)
            model = cfg.get('ai', {}).get('vision', {}).get('model', model)
        except Exception:
            pass
    return api_key, base_url, model


# ============================================================
# 摄像头操作
# ============================================================
def _list_cameras(max_index: int = 5) -> list:
    """枚举摄像头设备"""
    if cv2 is None:
        return []
    found = []
    for i in range(max_index):
        try:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                found.append({"index": i, "width": w, "height": h})
            cap.release()
        except Exception:
            continue
    return found


def _capture(index: int = 0, save: str = "", width: int = 1280, height: int = 720, retries: int = 3) -> dict:
    """拍照。返回图片信息；save 非空时保存到本地"""
    if cv2 is None:
        return {"ok": False, "error": "未安装 opencv-python，请先 pip install opencv-python"}
    last_err = None
    for attempt in range(retries):
        cap = None
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(index)  # 兜底后端
            if not cap.isOpened():
                last_err = f"无法打开摄像头 index={index}"
                continue
            if width > 0 and height > 0:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            # 预热几帧（自动曝光/白平衡稳定）
            for _ in range(5):
                cap.read()
            ok, frame = cap.read()
            if not ok or frame is None:
                last_err = "读取画面失败（可能被其他程序占用）"
                continue
            h, w = frame.shape[:2]
            result = {"ok": True, "index": index, "width": w, "height": h}
            if save:
                p = Path(save)
                p.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(p), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                result["path"] = str(p)
                result["size_bytes"] = p.stat().st_size if p.exists() else 0
            return result
        except Exception as e:
            last_err = str(e)
        finally:
            if cap is not None:
                cap.release()
    return {"ok": False, "error": last_err or "拍照失败"}


def _screen_capture(save: str) -> dict:
    """降级方案：无摄像头时截屏（mss），返回图片信息"""
    try:
        import mss
        with mss.MSS() as sct:
            mon = sct.monitors[1]
            img = sct.grab(mon)
            import mss.tools
            p = Path(save)
            p.parent.mkdir(parents=True, exist_ok=True)
            mss.tools.to_png(img.rgb, img.size, output=str(p))
            return {"ok": True, "source": "screen", "path": str(p),
                    "width": img.size[0], "height": img.size[1],
                    "size_bytes": p.stat().st_size if p.exists() else 0}
    except ImportError:
        return {"ok": False, "error": "mss 未安装，无法截屏降级"}
    except Exception as e:
        return {"ok": False, "error": f"截屏失败: {e}"}


def _encode_image_for_vlm(path: str, max_side: int = 1280, quality: int = 85) -> str:
    """读取图片 → 压缩 → base64 data URL（供 VLM 使用）"""
    import numpy as np
    img = cv2.imread(path)
    if img is None:
        from PIL import Image
        img = np.array(Image.open(path).convert('RGB'))[:, :, ::-1].copy()
    h, w = img.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return ""
    ext = 'jpg'
    return f"data:image/{ext};base64,{base64.b64encode(buf.tobytes()).decode('ascii')}"


# ============================================================
# 视觉大模型调用
# ============================================================
SYSTEM_PROMPT = (
    "你是一个机器人的视觉理解系统（眼睛）。请仔细观察图片，用中文输出结构化描述。"
    "输出 JSON，包含以下字段：\n"
    "{\"场景\":\"一句话概括场景\",\"物体\":[{\"名称\":\"...\",\"位置\":\"中心/左侧/...\",\"状态\":\"...\"}],"
    "\"人物\":[{\"人数\":0,\"动作\":\"...\",\"表情\":\"...\"}],\"文字\":\"图片中的文字\",\"异常\":\"值得注意的异常情况，无则写无\",\"建议\":\"机器人下一步应该做什么\"}"
)


def _vlm_analyze(image_path: str, prompt: str = "", timeout: int = 60) -> dict:
    """调用视觉大模型分析图片"""
    api_key, base_url, model = _load_vision_config()
    if not api_key:
        return {"ok": False, "error": "未配置 VISION_API_KEY（.env），无法调用视觉大模型"}
    if not image_path or not Path(image_path).exists():
        return {"ok": False, "error": f"图片不存在: {image_path}"}

    data_url = _encode_image_for_vlm(str(image_path))
    if not data_url:
        return {"ok": False, "error": "图片读取/压缩失败"}

    user_text = prompt or "请用中文详细描述这张图片的内容。"
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        }],
        "max_tokens": 1024,
        "temperature": 0.3,
        # 关闭思考模式：加快响应、省 token（仅对支持思考的模型生效，旧模型自动忽略）
        "thinking": {"type": "disabled"},
    }

    import requests
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
        content = resp.json()["choices"][0]["message"]["content"]
        # 尝试解析 JSON（模型可能包在 ```json 中）
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            structured = json.loads(text)
        except Exception:
            structured = {"raw": content}
        return {"ok": True, "model": model, "description": content, "structured": structured}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "视觉模型请求超时"}
    except Exception as e:
        return {"ok": False, "error": f"视觉模型调用失败: {e}"}


# ============================================================
# 变化检测（watch 模式用）
# ============================================================
def _frame_diff_ratio(frame_a, frame_b, threshold: int = 25) -> float:
    """计算两帧差异比例 0~1"""
    import numpy as np
    if frame_a is None or frame_b is None:
        return 1.0
    if frame_a.shape != frame_b.shape:
        return 1.0
    gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray_a, gray_b)
    changed = float((diff > threshold).sum()) / float(diff.size)
    return changed


# ============================================================
# 命令分发
# ============================================================
def cmd_list(args):
    cams = _list_cameras(args.max_index)
    if not cams:
        print("没有检测到摄像头。可尝试 camera_capture 时指定 --index，或用 see 模式自动降级为屏幕截图。")
        return
    print("检测到摄像头设备:")
    for c in cams:
        print(f"  index={c['index']}  分辨率 {c['width']}x{c['height']}")


def cmd_capture(args):
    if args.index < 0:
        # 自动寻找第一个可用摄像头
        cams = _list_cameras()
        if not cams:
            print(json.dumps({"ok": False, "error": "未检测到摄像头"}, ensure_ascii=False))
            return
        args.index = cams[0]["index"]
    r = _capture(index=args.index, save=args.save, width=args.width, height=args.height)
    if r.get("ok"):
        print(json.dumps({**r, "message": f"已拍照保存: {r['path']}"}, ensure_ascii=False))
    else:
        print(json.dumps(r, ensure_ascii=False))


def cmd_see(args):
    """拍照 + VLM 理解。无摄像头自动降级为屏幕截图"""
    save = args.save or str(ROOT / 'data' / 'camera_vision' / f'see_{time.strftime("%Y%m%d_%H%M%S")}.jpg')
    if args.image:
        shot = {"ok": True, "path": args.image, "source": "file"}
    else:
        cams = _list_cameras()
        if cams:
            idx = args.index if args.index >= 0 else cams[0]["index"]
            shot = _capture(index=idx, save=save, width=args.width, height=args.height)
            if shot.get("ok"):
                shot["source"] = "camera"
        else:
            shot = _screen_capture(save)
    if not shot.get("ok"):
        print(json.dumps(shot, ensure_ascii=False))
        return

    vlm = _vlm_analyze(shot["path"], prompt=args.prompt)
    result = {"ok": vlm["ok"], "source": shot.get("source", "?"), "image": shot["path"]}
    if vlm["ok"]:
        result["description"] = vlm["description"]
        result["structured"] = vlm.get("structured", {})
    else:
        result["error"] = vlm["error"]
    print(json.dumps(result, ensure_ascii=False))


def cmd_analyze(args):
    if not args.image:
        print(json.dumps({"ok": False, "error": "请指定 --image 图片路径"}, ensure_ascii=False))
        return
    vlm = _vlm_analyze(args.image, prompt=args.prompt)
    result = {"ok": vlm["ok"], "image": args.image}
    if vlm["ok"]:
        result["description"] = vlm["description"]
        result["structured"] = vlm.get("structured", {})
    else:
        result["error"] = vlm["error"]
    print(json.dumps(result, ensure_ascii=False))


def cmd_watch(args):
    """连续监控：间隔拍照 + 帧差变化检测 + 变化时触发 VLM 理解"""
    if cv2 is None:
        print(json.dumps({"ok": False, "error": "未安装 opencv-python"}, ensure_ascii=False))
        return
    cams = _list_cameras()
    if not cams:
        print(json.dumps({"ok": False, "error": "未检测到摄像头，watch 模式需要摄像头"}, ensure_ascii=False))
        return
    idx = args.index if args.index >= 0 else cams[0]["index"]
    out_dir = ROOT / 'data' / 'camera_vision'
    out_dir.mkdir(parents=True, exist_ok=True)

    print(json.dumps({"ok": True, "message": f"开始监控摄像头 index={idx}，共 {args.seconds}s，间隔 {args.interval}s（帧差>{(args.threshold*100):.0f}% 触发视觉理解）"}, ensure_ascii=False))

    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(json.dumps({"ok": False, "error": f"无法打开摄像头 {idx}"}, ensure_ascii=False))
        return
    try:
        prev = None
        start = time.time()
        while time.time() - start < args.seconds:
            ok, frame = cap.read()
            if not ok:
                time.sleep(1)
                continue
            ts = time.strftime("%H:%M:%S")
            diff = _frame_diff_ratio(prev, frame, threshold=args.threshold) if prev is not None else 1.0
            if diff > args.threshold or prev is None:
                path = str(out_dir / f'watch_{time.strftime("%Y%m%d_%H%M%S")}.jpg')
                cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                vlm = _vlm_analyze(path, prompt=args.prompt) if args.vlm else {"ok": False, "error": "skipped"}
                line = {"time": ts, "change": round(diff, 3), "image": path}
                if vlm.get("ok"):
                    line["description"] = vlm["description"]
                else:
                    line["note"] = "变化已记录（未调用视觉模型）"
                print(json.dumps(line, ensure_ascii=False))
                prev = frame.copy()
            time.sleep(args.interval)
    finally:
        cap.release()
    print(json.dumps({"ok": True, "message": "监控结束"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="摄像头视觉后端")
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list")
    p_list.add_argument("--max-index", type=int, default=5)

    p_cap = sub.add_parser("capture")
    p_cap.add_argument("--index", type=int, default=-1)
    p_cap.add_argument("--save", default="")
    p_cap.add_argument("--width", type=int, default=1280)
    p_cap.add_argument("--height", type=int, default=720)

    p_see = sub.add_parser("see")
    p_see.add_argument("--index", type=int, default=-1)
    p_see.add_argument("--save", default="")
    p_see.add_argument("--width", type=int, default=1280)
    p_see.add_argument("--height", type=int, default=720)
    p_see.add_argument("--image", default="", help="直接分析已有图片（跳过拍照）")
    p_see.add_argument("--prompt", default="", help="自定义理解指令")

    p_ana = sub.add_parser("analyze")
    p_ana.add_argument("--image", required=True)
    p_ana.add_argument("--prompt", default="")

    p_watch = sub.add_parser("watch")
    p_watch.add_argument("--index", type=int, default=-1)
    p_watch.add_argument("--seconds", type=int, default=30)
    p_watch.add_argument("--interval", type=int, default=5)
    p_watch.add_argument("--threshold", type=float, default=0.05)
    p_watch.add_argument("--vlm", action="store_true", help="变化时调用视觉大模型理解")
    p_watch.add_argument("--prompt", default="")

    args = parser.parse_args()
    if args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "capture":
        cmd_capture(args)
    elif args.cmd == "see":
        cmd_see(args)
    elif args.cmd == "analyze":
        cmd_analyze(args)
    elif args.cmd == "watch":
        cmd_watch(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
