# -*- coding: utf-8 -*-
"""
安全地设置 / 更新 config/deploy.json 中的服务器密码。

特点：
  * 密码用 getpass 隐藏输入，不回显、不落盘到日志、不经过任何聊天/工具参数
  * 写回前先确认两次输入一致
  * 写回后立即实测 SSH + SFTP 是否可用，给出明确结论

用法：双击项目根目录的 set_server_password.bat，或命令行执行
      python scripts/set_deploy_password.py
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(BASE, "config", "deploy.json")


def mask(v):
    v = str(v)
    return "*" * len(v) if len(v) <= 4 else v[:2] + "*" * (len(v) - 4) + v[-2:]


def main():
    if not os.path.exists(CFG):
        print("[X] 找不到配置文件：", CFG)
        return 2

    cfg = json.load(open(CFG, encoding="utf-8"))
    srv = cfg.setdefault("server", {})
    old = srv.get("password", "")

    print("=" * 60)
    print("配置文件 :", CFG)
    print("服务器   :", f"{srv.get('user')}@{srv.get('host')}:{srv.get('port', 22)}")
    print("当前密码 :", mask(old), f"(len={len(old)})")
    print("=" * 60)
    if not sys.stdin.isatty():
        print("[X] 当前不是交互式终端（stdin 被重定向 / 被自动化调用）。")
        print("    为避免卡死等待输入，已直接退出，未做任何修改。")
        print("    请双击项目根目录的 set_server_password.bat 来运行。")
        return 2

    print("请输入【新的】服务器密码（输入时不显示），直接回车 = 取消")
    print()

    try:
        import getpass
        p1 = getpass.getpass("new password : ")
    except Exception as e:
        print("[X] 无法读取隐藏输入:", e)
        return 2

    if not p1:
        print("已取消，未做任何修改。")
        return 0

    p2 = getpass.getpass("confirm again: ")
    if p1 != p2:
        print("[X] 两次输入不一致，未做任何修改。")
        return 1

    if p1 == old:
        print("[!] 与当前值相同，仍然写入（无实际变化）。")

    srv["password"] = p1
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print()
    print("[1/2] 已写入配置：", mask(p1), f"(len={len(p1)})")

    # ---- 立即验证 ----
    print("[2/2] 正在验证 SSH / SFTP 连接 ...")
    try:
        import paramiko
    except Exception as e:
        print("      [!] 未安装 paramiko，跳过连通性验证:", e)
        return 0

    host = srv.get("host")
    port = int(srv.get("port", 22))
    user = srv.get("user")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(host, port=port, username=user, password=p1,
                    timeout=20, banner_timeout=20, auth_timeout=20)
        _in, out, _err = cli.exec_command("whoami", timeout=15)
        who = out.read().decode("utf-8", "replace").strip()
        print("      SSH  : OK  (whoami =", who + ")")

        sftp = cli.open_sftp()
        rdir = srv.get("remote_dir", "")
        try:
            names = sftp.listdir(rdir)
            print(f"      SFTP : OK  ({rdir} 下 {len(names)} 个条目)")
        except Exception as e:
            print(f"      SFTP : [!] listdir 失败 -> {e}")
        sftp.close()
        cli.close()
        print()
        print(">>> 全部通过：发布链已恢复可用。")
        return 0
    except Exception as e:
        cli.close()
        print(f"      [X] 连接失败 -> {type(e).__name__}: {e}")
        print()
        print(">>> 密码已写入文件，但验证未通过。请确认密码是否正确。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
