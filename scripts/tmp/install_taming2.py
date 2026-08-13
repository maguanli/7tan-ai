# -*- coding: utf-8 -*-
import io, sys, os, shutil, zipfile, urllib.request, tempfile, subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
venv_sp = r"G:\AI_Video\stable-diffusion-webui\venv\Lib\site-packages"

# 下载 taming-transformers GitHub 源码
for branch in ["main", "master"]:
    url = f"https://codeload.github.com/CompVis/taming-transformers/zip/refs/heads/{branch}"
    zp = os.path.join(tempfile.gettempdir(), "taming.zip")
    try:
        urllib.request.urlretrieve(url, zp)
        print("downloaded", branch, os.path.getsize(zp))
    except Exception as e:
        print("fail", branch, e)
        continue
    tmp = os.path.join(tempfile.gettempdir(), "taming_src")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        z.extractall(tmp)
    inner = os.path.join(tmp, names[0].split("/")[0])
    src_taming = os.path.join(inner, "taming")
    print("taming src exists:", os.path.isdir(src_taming))
    if os.path.isdir(src_taming):
        # 备份旧的
        dst = os.path.join(venv_sp, "taming")
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src_taming, dst)
        # 验证
        code = "from taming.modules.vqvae.quantize import VectorQuantizer2 as VQ; print('VectorQuantizer2 OK')"
        r = subprocess.run([r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe", "-c", code],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        print("verify rc:", r.returncode, r.stdout, r.stderr[-800:] if r.stderr else "")
        if r.returncode == 0:
            sys.exit(0)
    break
print("FAILED")
sys.exit(1)
