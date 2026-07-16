"""临时构建脚本 - 绕过沙盒直接运行"""
import subprocess, os, sys

os.chdir(r"D:\7tan\7tanAI")

# 使用 .venv 的 python 来运行 PyInstaller
python_exe = r"D:\7tan\7tanAI\.venv\Scripts\python.exe"

print(f"Python: {python_exe}")
print(f"Exists: {os.path.exists(python_exe)}")

# 第一步：确认 PyInstaller
print("\n[1/3] 检查 PyInstaller...")
r = subprocess.run([python_exe, "-m", "pip", "install", "pyinstaller", "--upgrade", "-q"],
                   capture_output=True, text=True, timeout=120)
print(r.stdout[-500:] if r.stdout else "", r.stderr[-500:] if r.stderr else "")

# 第二步：清理旧构建
print("\n[2/3] 清理旧构建...")
import shutil
for d in ["dist/7tan-editor", "build"]:
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
        print(f"  已删除: {d}")

# 第三步：PyInstaller 打包
print("\n[3/3] PyInstaller 打包中（5-15分钟）...")
sys.stdout.flush()

r = subprocess.run(
    [python_exe, "-m", "PyInstaller", "build.spec", "--noconfirm"],
    capture_output=True, text=True, timeout=900,
    cwd=r"D:\7tan\7tanAI",
    env={**os.environ, "PYTHONUNBUFFERED": "1"}
)

print(f"\n返回码: {r.returncode}")
if r.stdout:
    print("=== STDOUT(最后3000) ===")
    print(r.stdout[-3000:])
if r.stderr:
    print("=== STDERR(最后1000) ===")
    print(r.stderr[-1000:])

if r.returncode == 0:
    print("\n✅ 构建成功！")
    # 复制配置文件
    import shutil as sh
    dst = r"D:\7tan\7tanAI\dist\7tan-editor"
    if os.path.exists(f"{dst}/config"):
        pass
    else:
        os.makedirs(f"{dst}/config", exist_ok=True)
    sh.copy2(r"D:\7tan\7tanAI\config\config.yaml", f"{dst}/config/config.yaml")
    sh.copy2(r"D:\7tan\7tanAI\config\sensitive_words.txt", f"{dst}/config/sensitive_words.txt")
    print("配置文件已复制")
else:
    print("\n❌ 构建失败！")
