# -*- coding: utf-8 -*-
"""
根目录调试残留归档：git mv 到 scripts/tmp/
保留：main.py / README / *.spec / *.bat / *.ps1 / requirements / integrity.json /
      .gitignore / .env.example / index.html / resign_hashes.py / upload_*.py /
      auto_publish_*.py / resume_publish_1010.py / 中文名文件
"""
import os
import re
import subprocess
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\7tan\7tanAI"

# 读取当前根目录跟踪文件
out = subprocess.check_output(["git", "ls-files"], cwd=ROOT,
                              text=True, encoding="utf-8", errors="replace")
root_files = [f for f in out.splitlines() if "/" not in f]

# 白名单（保留）
KEEP = {
    ".env.example", ".gitignore",
    "7tan-updater-debug.spec", "7tan-updater.spec", "build.spec",
    "README.md", "main.py", "requirements.txt", "integrity.json",
    "index.html", "resign_hashes.py",
    "build.bat", "build_and_sync.bat", "rebuild.bat", "start.bat",
    "start.sh", "run_check.bat", "git-init.bat", "git-save.bat",
    "apply_pyd_update.bat", "fix_browser.ps1",
    "auto_publish_107.bat", "auto_publish_1010.py", "auto_publish_1011.py",
    "auto_publish_107.py", "auto_publish_108.py", "auto_publish_109.py",
    "auto_publish_107_patch.py", "resume_publish_1010.py",
    "upload_robot_head.py", "upload_robot_head_v2.py", "upload_robot_head_v3.py",
    "upload_robot_head_v4_diag.py", "upload_robot_head_v5_diag.py",
    "upload_robot_head_v6_fix.py", "upload_updates_index.py",
    "run_resume_1010.bat",
}
# 中文/特殊文件名一律保留
def keep_by_name(name: str) -> bool:
    if name in KEEP:
        return True
    if not name.isascii():
        return True
    return False

# 归档模式：明显的一次性调试脚本 / 诊断文本 / 截图
ARCHIVE_PATTERNS = [
    re.compile(r"^_.*\.(py|txt)$"),            # _ 开头临时脚本/OCR文本
    re.compile(r"^qq_.*\.(py|txt)$"),          # QQ 调试
    re.compile(r"^check_.*\.py$"),             # 检查类调试脚本
    re.compile(r"^tmp_.*\.py$"),               # 临时脚本
    re.compile(r"^start_webui.*\.py$"),        # SD WebUI 启动
    re.compile(r"^downgrade_.*\.py$"),         # 降级调试
    re.compile(r"^install_.*\.py$"),           # 安装调试
    re.compile(r"^make_cover.*\.py$"),         # 封面生成
    re.compile(r"^generate_.*\.py$"),          # 图片生成
    re.compile(r"^article_.*\.(html|txt)$"),   # 文章素材
    re.compile(r"^chat_.*\.png$"),             # 截图
    re.compile(r"^pip_packages.*\.txt$"),      # 环境清单
    re.compile(r"^(env_test_rel|build_full_log|file_version_info)\.(txt|py|json)$"),
]

EXTRA_ARCHIVE = {
    "start_sd.py", "wait_sd_gentle.py", "fix_and_start_webui.py", "diag_webui.py",
    "final_start.py", "clone_sd_repo.py", "inspect_sd_repo.py", "replace_ldm.py",
    "setup_clip_cache.py", "setup_cython.py", "free_ports.py", "check_repos.py",
    "fix_repos.py", "search_forks.py", "explore_env.py", "decrypt_key_test.py",
    "compare_versions.py", "download_gm.py", "download_sd_zip.py",
    "download_sd_zip2.py", "download_sd_zip3.py", "fetch_midas.py",
    "fetch_midas2.py", "fetch_updates_index.py", "find_original.py",
    "find_plugin.py", "fix_bug.py", "launch_batch.py", "start_and_wait.py",
    "list_windows.py", "list_clip_files.py", "read_bat.py", "minimize_7tan.py",
    "ocr_region.py", "git_original_tools.py", "final_verify_1010.py",
    "check_website_download.py", "check_website_root.py", "batch_gen_frames.py",
    "measure_compare_covers.py", "process_marriage_images.py",
    "left_top.png", "screen_now.png", "wechat_after_click.png",
    "wechat_now.png", "wechat_open.png", "check_bundled.py",
    "check_ch3_size.py", "check_clone.py", "check_cpu.py",
    "check_guard_toolchain.py", "check_hash.py", "check_img_sizes.py",
    "check_ports2.py", "check_procs.py", "check_procs2.py", "check_sd.py",
    "check_sd2.py", "check_sd3.py", "check_sd4.py", "check_sd5.py",
}

to_archive = []
for f in root_files:
    if keep_by_name(f):
        continue
    if f in EXTRA_ARCHIVE:
        to_archive.append(f)
        continue
    if any(p.match(f) for p in ARCHIVE_PATTERNS):
        to_archive.append(f)

to_archive = sorted(set(to_archive))

# 执行 git mv
dest_dir = os.path.join(ROOT, "scripts", "tmp")
os.makedirs(dest_dir, exist_ok=True)
moved, failed = [], []
for f in to_archive:
    src = os.path.join(ROOT, f)
    if not os.path.exists(src):
        continue
    r = subprocess.run(["git", "mv", f, os.path.join("scripts", "tmp", f)],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode == 0:
        moved.append(f)
    else:
        failed.append((f, r.stderr.strip()))

print("archived:", len(moved))
for f in moved[:20]:
    print("  ", f)
if len(moved) > 20:
    print("   ... +%d more" % (len(moved) - 20))
if failed:
    print("FAILED:")
    for f, e in failed:
        print("  ", f, "->", e)
