# -*- coding: utf-8 -*-
import io, sys, os, shutil, zipfile, urllib.request, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
midas_dir = r"G:\AI_Video\stable-diffusion-webui\repositories\stable-diffusion-stability-ai\ldm\modules\midas"

url = "https://codeload.github.com/yuanyixiong/stable-diffusion-stability-ai/zip/refs/heads/main"
zp = os.path.join(tempfile.gettempdir(), "sd_fork.zip")
print("downloading...", flush=True)
try:
    urllib.request.urlretrieve(url, zp)
    print("downloaded:", os.path.getsize(zp))
except Exception as e:
    print("fail:", e)
    sys.exit(1)

tmp = os.path.join(tempfile.gettempdir(), "sd_fork_src")
if os.path.isdir(tmp):
    shutil.rmtree(tmp)
os.makedirs(tmp)
with zipfile.ZipFile(zp) as z:
    names = z.namelist()
    print("entries:", len(names))
    z.extractall(tmp)
inner = os.path.join(tmp, names[0].split("/")[0])
src_midas = os.path.join(inner, "ldm", "modules", "midas")
print("src midas exists:", os.path.isdir(src_midas))
if os.path.isdir(src_midas):
    if os.path.isdir(midas_dir):
        shutil.rmtree(midas_dir)
    shutil.copytree(src_midas, midas_dir)
    print("copied:", os.listdir(midas_dir))
    # 验证
    import subprocess
    code = "from ldm.modules.midas.api import load_midas; print('load_midas OK')"
    r = subprocess.run([r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe", "-c", code],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                       cwd=r"G:\AI_Video\stable-diffusion-webui")
    print("verify rc:", r.returncode)
    print(r.stdout)
    print((r.stderr or "")[-1000:])
else:
    print("midas not in fork, listing ldm/modules:", os.listdir(os.path.join(inner, "ldm", "modules"))[:30])
