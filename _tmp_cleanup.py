import os, glob

# 清理临时脚本
tmp_files = [
    '_tmp_diskcheck.py', '_tmp_checkbuild.py', '_tmp_build_launcher.py',
    '_tmp_wait.py', '_tmp_verify.py', '_tmp_sftp_probe.py',
    '_tmp_sftp_out.txt', '_tmp_upload.py', '_tmp_upload_log.txt',
]
for f in tmp_files:
    p = os.path.join(r'D:\7tan\7tanAI', f)
    if os.path.exists(p):
        os.remove(p)
        print(f"removed {f}")
print("cleanup done")
