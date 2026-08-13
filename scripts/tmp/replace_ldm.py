# -*- coding: utf-8 -*-
import io, sys, os, shutil, zipfile, urllib.request, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
repo = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai"

# 检查临时目录是否还有 fork 源码
tmp = os.path.join(tempfile.gettempdir(), "sd_fork_src")
inner = None
if os.path.isdir(tmp):
    for x in os.listdir(tmp):
        if os.path.isdir(os.path.join(tmp, x)):
            inner = os.path.join(tmp, x)
            break
if not inner or not os.path.isdir(os.path.join(inner, "ldm")):
    print("need re-download...")
    url = "https://codeload.github.com/yuanyixiong/stable-diffusion-stability-ai/zip/refs/heads/main"
    zp = os.path.join(tempfile.gettempdir(), "sd_fork.zip")
    urllib.request.urlretrieve(url, zp)
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        z.extractall(tmp)
    inner = os.path.join(tmp, names[0].split("/")[0])

src_ldm = os.path.join(inner, "ldm")
print("src ldm exists:", os.path.isdir(src_ldm))

dst_ldm = os.path.join(repo, "ldm")
# 备份旧 ldm
bak = os.path.join(repo, "ldm_compvis_bak")
if os.path.isdir(dst_ldm) and not os.path.isdir(bak):
    shutil.move(dst_ldm, bak)
    print("old ldm backed up -> ldm_compvis_bak")
if os.path.isdir(dst_ldm):
    shutil.rmtree(dst_ldm)
shutil.copytree(src_ldm, dst_ldm)
print("new ldm copied")

# 验证关键属性
import subprocess
code = ("import sys; sys.path.insert(0, r'%s'); "
        "import ldm.modules.attention as a; "
        "print('ATTENTION_MODES:', hasattr(a.BasicTransformerBlock, 'ATTENTION_MODES')); "
        "from ldm.modules.midas.api import load_midas; print('midas OK')" % repo)
r = subprocess.run([r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe", "-c", code],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("verify rc:", r.returncode)
print(r.stdout)
print((r.stderr or "")[-1500:])
