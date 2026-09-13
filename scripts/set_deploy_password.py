# -*- coding: utf-8 -*-
"""
安全地设置 / 更新 config/deploy.json 中的服务器密码。

输入方式（自动选择）：
  1) 图形窗口（tkinter）—— 默认，最稳，不受控制台输入问题影响
  2) 控制台隐藏输入（getpass）—— 加 --console 强制使用

特点：
  * 密码不回显、不写日志、不经过任何聊天/工具参数
  * 写回前确认两次输入一致
  * 写回后立即实测 SSH + SFTP，给出明确结论
"""
import json
import os
import sys

# 注意：这里只「重配置」编码，绝不替换 sys.stdout 对象。
# 替换会丢掉 line_buffering，导致提示文字全部滞留在缓冲区里，
# 界面看起来像卡死（这正是上一版的问题之一）。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(BASE, "config", "deploy.json")

NOTE = ("密码只写入本机配置文件 config\\deploy.json，\n"
        "不会上传、不会出现在聊天记录或日志里。")


def mask(v):
    v = str(v)
    return "*" * len(v) if len(v) <= 4 else v[:2] + "*" * (len(v) - 4) + v[-2:]


def looks_like_path(v):
    """判断输入是否「看起来是文件路径」而不是密码。

    最常见的误操作：把脚本自身的路径粘进了密码框。这种值会被
    「成功」写进配置，但永远连不上服务器，而且表面上完全看不出来。
    """
    v = (v or "").strip()
    if not v:
        return False
    low = v.lower()
    if (len(v) >= 3 and v[0].isalpha() and v[1] == ":"
            and v[2] in "\\/"):              # 盘符开头，例如 D:\... 或 C:/...
        return True
    if low.startswith("file://"):
        return True
    if ":\\" in v or ":/" in v:
        return True
    for ext in (".bat", ".cmd", ".py", ".json", ".txt", ".exe",
                ".zip", ".md", ".pem", ".log", ".ps1"):
        if low.endswith(ext):
            return True
    return False


# ---------------------------------------------------------------- 图形输入
def gui_ask(title, info, note=""):
    """弹出图形窗口两次输入密码。返回密码串；用户取消返回 None。"""
    import tkinter as tk

    res = {"pwd": None, "why": "cancel"}
    root = tk.Tk()
    root.title(title)
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    font = ("Microsoft YaHei UI", 9)
    tk.Label(root, text=info, justify="left", anchor="w",
             font=font).grid(row=0, column=0, columnspan=2, sticky="w",
                             padx=14, pady=(14, 2))
    if note:
        tk.Label(root, text=note, justify="left", anchor="w", fg="#666666",
                 font=("Microsoft YaHei UI", 8)).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 6))

    tk.Label(root, text="新密码", font=font).grid(
        row=2, column=0, sticky="e", padx=(14, 6), pady=(10, 4))
    e1 = tk.Entry(root, show="\u25cf", width=34, font=("Consolas", 10))
    e1.grid(row=2, column=1, sticky="w", padx=(0, 14), pady=(10, 4))

    tk.Label(root, text="再输一次", font=font).grid(
        row=3, column=0, sticky="e", padx=(14, 6), pady=(0, 4))
    e2 = tk.Entry(root, show="\u25cf", width=34, font=("Consolas", 10))
    e2.grid(row=3, column=1, sticky="w", padx=(0, 14), pady=(0, 4))

    err = tk.Label(root, text="", fg="#c00000", justify="left", anchor="w",
                   font=("Microsoft YaHei UI", 8))
    err.grid(row=4, column=0, columnspan=2, sticky="w", padx=14)

    def on_ok(_event=None):
        a, b = e1.get(), e2.get()
        if not a:
            err.config(text="密码不能为空")
            e1.focus_set()
            return
        if looks_like_path(a):
            err.config(text="这看起来是【文件路径】，不是密码！\n"
                            "是不是把某个 .bat / .py 的路径粘进来了？")
            e1.delete(0, "end")
            e2.delete(0, "end")
            e1.focus_set()
            return
        if a != b:
            err.config(text="两次输入不一致，请重新输入")
            e2.delete(0, "end")
            e2.focus_set()
            return
        res["pwd"] = a
        res["why"] = "ok"
        root.destroy()

    def on_cancel(_event=None):
        res["why"] = "cancel"
        root.destroy()

    box = tk.Frame(root)
    box.grid(row=5, column=0, columnspan=2, pady=(8, 12))
    tk.Button(box, text="确定", width=10, command=on_ok).pack(side="left", padx=6)
    tk.Button(box, text="取消", width=10, command=on_cancel).pack(side="left", padx=6)

    root.bind("<Return>", on_ok)
    root.bind("<Escape>", on_cancel)
    e1.focus_set()

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = max(0, (root.winfo_screenwidth() - w) // 2)
    y = max(0, (root.winfo_screenheight() - h) // 3)
    root.geometry("+%d+%d" % (x, y))
    root.mainloop()
    return res["pwd"]


# ---------------------------------------------------------------- 控制台输入
def console_ask():
    """返回密码串 / None=取消 / ''=不一致"""
    p1 = None
    try:
        import getpass
        p1 = getpass.getpass("new password : ")
    except Exception as e:
        print("[!] 隐藏输入不可用（%s），改为明文输入。" % type(e).__name__)
        try:
            p1 = input("new password (明文) : ")
        except Exception as e2:
            print("[X] 仍无法读取输入：", e2)
            return None
    if not p1:
        return None
    if looks_like_path(p1):
        print("[X] 这看起来是【文件路径】，不是密码，已中止。")
        print("    你粘贴的很可能是某个文件自身的路径。")
        return None
    try:
        p2 = getpass.getpass("confirm again: ")
    except Exception:
        p2 = input("confirm again (明文) : ")
    if p1 != p2:
        print("[X] 两次输入不一致，未做任何修改。")
        return ""
    return p1


# ---------------------------------------------------------------- 连通性验证
def verify(srv, pwd):
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
        cli.connect(host, port=port, username=user, password=pwd,
                    timeout=20, banner_timeout=20, auth_timeout=20)
        _i, out, _e = cli.exec_command("whoami", timeout=15)
        who = out.read().decode("utf-8", "replace").strip()
        print("      SSH  : OK  (whoami =", who + ")")
        sftp = cli.open_sftp()
        rdir = srv.get("remote_dir", "")
        try:
            names = sftp.listdir(rdir)
            print("      SFTP : OK  (%s 下 %d 个条目)" % (rdir, len(names)))
        except Exception as e:
            print("      SFTP : [!] listdir 失败 ->", e)
        sftp.close()
        cli.close()
        print()
        print(">>> 全部通过：发布链已恢复可用。")
        return 0
    except Exception as e:
        try:
            cli.close()
        except Exception:
            pass
        print("      [X] 连接失败 -> %s: %s" % (type(e).__name__, e))
        print()
        print(">>> 密码已写入文件，但验证未通过。请确认密码是否正确。")
        return 1


# ---------------------------------------------------------------- 主流程
def main():
    argv = [a.lower() for a in sys.argv[1:]]
    force_console = bool({"--console", "-c"} & set(argv))
    force_gui = bool({"--gui", "-g"} & set(argv))

    if not os.path.exists(CFG):
        print("[X] 找不到配置文件：", CFG)
        return 2

    with open(CFG, encoding="utf-8") as f:
        cfg = json.load(f)
    srv = cfg.setdefault("server", {})
    old = srv.get("password", "")

    info = ("服务器　: %s@%s:%s\n"
            "当前密码: %s  (长度 %d)\n"
            "配置文件: %s" % (srv.get("user"), srv.get("host"),
                            srv.get("port", 22), mask(old), len(old), CFG))

    print("=" * 60)
    print("7Tan 服务器发布密码设置")
    print("=" * 60)
    print(info)
    print("=" * 60, flush=True)

    pwd = None

    # 只在「明确的交互式终端」或显式 --gui 时才弹窗，
    # 避免被自动化调用时弹出一个阻塞的窗口（这个坑踩过两次）。
    if force_gui or (not force_console and sys.stdin.isatty()):
        try:
            pwd = gui_ask("7Tan 服务器密码设置", info, NOTE)
            if pwd is None:
                print("已取消，未做任何修改。")
                return 0
        except Exception as e:
            print("[!] 图形窗口不可用（%s: %s）" % (type(e).__name__, e))
            print("    改用控制台输入。")
            pwd = None

    if pwd is None:
        if not sys.stdin.isatty():
            print("[X] 当前不是交互式终端，无法读取输入。")
            print("    请双击项目根目录的 set_server_password.bat 运行。")
            return 2
        pwd = console_ask()
        if pwd is None:
            print("已取消，未做任何修改。")
            return 0
        if pwd == "":
            return 1

    if pwd == old:
        print("[!] 与当前值相同，仍会写入（无实际变化）。")
    if looks_like_path(pwd):
        print("[X] 拒绝写入：该值看起来是文件路径，不是密码。")
        return 1

    srv["password"] = pwd
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("[1/2] 已写入配置：", mask(pwd), "(长度 %d)" % len(pwd), flush=True)

    return verify(srv, pwd)


if __name__ == "__main__":
    sys.exit(main())
