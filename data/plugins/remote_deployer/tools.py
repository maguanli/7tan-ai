
"""
远程部署与 CI/CD 插件 — ADB安装、远程部署、自动化流水线
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

import subprocess
import os
import json
import time
import signal
from pathlib import Path

# ========== 安全命令执行（加固：超时强制杀进程树） ==========
_WIN = os.name == "nt"
MAX_TOOL_TIMEOUT = 600  # 任何命令硬上限 10 分钟，防止误传超大超时拖死 UI


def _kill_tree(proc):
    """强制终止整个进程树（Windows: taskkill /T /F；POSIX: killpg）"""
    try:
        if _WIN:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _run_cmd_safe(cmd, cwd=None, timeout=120, shell=False):
    """安全执行命令：Popen + 进程组隔离 + 超时强制杀进程树。

    - Windows: CREATE_NEW_PROCESS_GROUP + CREATE_NO_WINDOW
    - 超时后 taskkill /T /F 杀掉全部子进程，绝不残留挂起进程
    - timeout 上限 MAX_TOOL_TIMEOUT，防止调用方误传超大值
    """
    timeout = min(max(int(timeout or 120), 1), MAX_TOOL_TIMEOUT)
    flags = 0
    if _WIN:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
            cmd, shell=shell, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            creationflags=flags,
        )
    except FileNotFoundError:
        return "", "Shell 不可用或命令未找到", -1
    except OSError as e:
        return "", f"系统错误: {e}", -1

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return (stdout or ""), (stderr or ""), proc.returncode
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            stdout, stderr = "", ""
        return (stdout or ""), f"⏱ 命令超时（{timeout}s），已强制终止整个进程树", -1


def _ssh_base_cmd(port: int = 22) -> list:
    """SSH 基础参数：连接 15s 快速失败 + 心跳保活 + 免交互"""
    return [
        "ssh", "-p", str(port),
        "-o", "ConnectTimeout=15",
        "-o", "ServerAliveInterval=10",
        "-o", "ServerAliveCountMax=3",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
    ]

# ========== ADB 手机部署 ==========

@register_tool(name="adb_devices",description="列出所有已连接的Android设备",parameters={},category="devops")
def adb_devices() -> dict:
    """列出所有连接的 ADB 设备"""
    result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=15)
    lines = result.stdout.strip().split("\n")[1:]  # 跳过 "List of devices"
    devices = []
    for line in lines:
        if line.strip() and "device" in line:
            parts = line.split()
            devices.append({"serial": parts[0], "status": parts[1], "info": " ".join(parts[2:])})
    return {"success": True, "devices": devices, "count": len(devices)}

@register_tool(name="adb_install",description="通过ADB安装APK到Android设备",parameters={"apk_path":{"type":"string","description":"APK文件路径"},"device":{"type":"string","description":"目标设备","default":""}},category="devops")
def adb_install(apk_path: str, device: str = "") -> dict:
    """安装 APK 到手机（通过 ADB）"""
    if not os.path.exists(apk_path):
        return {"success": False, "error": f"APK 不存在: {apk_path}"}
    
    apk_size = os.path.getsize(apk_path) / (1024*1024)
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["install", "-r", apk_path]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return {
        "success": "Success" in result.stdout,
        "apk": apk_path,
        "size_mb": round(apk_size, 2),
        "stdout": result.stdout,
        "stderr": result.stderr
    }

@register_tool(name="adb_uninstall",description="通过ADB卸载Android应用",parameters={"package_name":{"type":"string","description":"包名"},"device":{"type":"string","description":"目标设备","default":""}},category="devops")
def adb_uninstall(package_name: str, device: str = "") -> dict:
    """卸载手机上的应用"""
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["uninstall", package_name]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return {"success": "Success" in result.stdout, "stdout": result.stdout}

@register_tool(name="adb_list_packages",description="列出Android设备已安装的应用包",parameters={"device":{"type":"string","description":"设备","default":""},"filter_str":{"type":"string","description":"过滤关键词","default":""}},category="devops")
def adb_list_packages(device: str = "", filter_str: str = "") -> dict:
    """列出手机已安装的包"""
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["shell", "pm", "list", "packages"]
    if filter_str:
        cmd[-1] += f" | grep {filter_str}"
    
    result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True, timeout=30)
    packages = [p.replace("package:", "") for p in result.stdout.strip().split("\n") if p]
    return {"success": True, "packages": packages, "count": len(packages)}

@register_tool(name="adb_screenshot",description="通过ADB截取Android设备屏幕",parameters={"device":{"type":"string","description":"设备","default":""},"save_path":{"type":"string","description":"保存路径","default":""}},category="devops")
def adb_screenshot(device: str = "", save_path: str = "") -> dict:
    """截取手机屏幕并拉取到本地"""
    cmd_prefix = ["adb"]
    if device:
        cmd_prefix += ["-s", device]
    
    # 手机端截图
    subprocess.run(cmd_prefix + ["shell", "screencap", "-p", "/sdcard/screenshot_temp.png"],
                   capture_output=True, timeout=15)
    # 拉取到本地
    if not save_path:
        save_path = f"data/screenshots/phone_{int(time.time())}.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    subprocess.run(cmd_prefix + ["pull", "/sdcard/screenshot_temp.png", save_path],
                   capture_output=True, timeout=15)
    return {"success": os.path.exists(save_path), "local_path": save_path}

@register_tool(name="adb_shell",description="在Android设备上执行Shell命令",parameters={"command":{"type":"string","description":"命令"},"device":{"type":"string","description":"设备","default":""}},category="devops")
def adb_shell(command: str, device: str = "") -> dict:
    """在手机上执行 shell 命令"""
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["shell"] + command.split()
    stdout, stderr, rc = _run_cmd_safe(cmd, timeout=30)
    return {"success": rc == 0, "stdout": stdout, "stderr": stderr}

# ========== 远程服务器部署 ==========

@register_tool(name="rsync_deploy",description="通过rsync同步文件到远程服务器",parameters={"local_path":{"type":"string","description":"本地路径"},"remote_dest":{"type":"string","description":"远程路径"},"remote_host":{"type":"string","description":"远程主机","default":""}},category="devops")
def rsync_deploy(local_path: str, remote_dest: str, remote_host: str = "", 
                 remote_user: str = "", exclude: str = "") -> dict:
    """使用 rsync 部署到远程服务器"""
    cmd = ["rsync", "-avz", "--timeout=15", "--progress"]
    if exclude:
        for pattern in exclude.split(","):
            cmd += ["--exclude", pattern.strip()]
    
    cmd.append(local_path.rstrip("/") + "/")
    
    if remote_host:
        target = f"{remote_user}@{remote_host}:{remote_dest}" if remote_user else f"{remote_host}:{remote_dest}"
    else:
        target = remote_dest
    cmd.append(target)
    
    stdout, stderr, rc = _run_cmd_safe(cmd, timeout=120)
    return {"success": rc == 0, "stdout": stdout, "stderr": stderr}

@register_tool(name="scp_upload",description="通过SCP上传文件到远程服务器",parameters={"local_file":{"type":"string","description":"本地文件"},"remote_path":{"type":"string","description":"远程路径"},"host":{"type":"string","description":"主机地址"}},category="devops")
def scp_upload(local_file: str, remote_path: str, host: str, user: str = "", port: int = 22) -> dict:
    """SCP 上传单个文件到远程服务器"""
    if not os.path.exists(local_file):
        return {"success": False, "error": f"文件不存在: {local_file}"}
    
    cmd = ["scp", "-P", str(port), "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]
    if user and host:
        target = f"{user}@{host}:{remote_path}"
    else:
        target = remote_path
    cmd += [local_file, target]
    
    stdout, stderr, rc = _run_cmd_safe(cmd, timeout=60)
    return {"success": rc == 0, "stdout": stdout, "stderr": stderr}

@register_tool(name="ssh_execute",description="通过SSH远程执行命令",parameters={"host":{"type":"string","description":"主机"},"command":{"type":"string","description":"命令"}},category="devops")
def ssh_execute(host: str, command: str, user: str = "", port: int = 22) -> dict:
    """在远程服务器上执行命令"""
    cmd = _ssh_base_cmd(port)
    if user:
        host = f"{user}@{host}"
    cmd += [host, command]
    
    stdout, stderr, rc = _run_cmd_safe(cmd, timeout=30)
    return {
        "success": rc == 0,
        "exit_code": rc,
        "stdout": stdout,
        "stderr": stderr
    }

@register_tool(name="gradle_build",description="执行Gradle构建任务",parameters={"project_path":{"type":"string","description":"项目路径"},"task":{"type":"string","description":"构建任务","default":"assembleRelease"}},category="devops")
def gradle_build(project_path: str, task: str = "assembleRelease") -> dict:
    """执行 Gradle 构建"""
    p = Path(project_path)
    if not p.exists():
        return {"success": False, "error": f"项目路径不存在: {project_path}", "artifacts": []}
    
    # 检测 gradlew
    if (p / "gradlew.bat").exists():
        cmd = [str(p / "gradlew.bat"), task]
    elif (p / "gradlew").exists():
        cmd = [str(p / "gradlew"), task]
    else:
        cmd = ["gradle", task]
    
    result = subprocess.run(cmd, cwd=str(p), capture_output=True, text=True, timeout=600)
    
    # 查找生成的 APK
    artifacts = []
    apk_dir = p / "app" / "build" / "outputs" / "apk"
    if apk_dir.exists():
        for apk in apk_dir.rglob("*.apk"):
            artifacts.append({
                "path": str(apk),
                "name": apk.name,
                "size_mb": round(apk.stat().st_size / (1024*1024), 2)
            })
    
    return {
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-1000:],
        "artifacts": artifacts
    }


def _resolve_cwd(cwd: str) -> str:
    """验证并解析工作目录，无效时回退到当前目录"""
    if cwd and cwd.strip():
        try:
            cwd_path = Path(cwd.strip()).resolve()
            if cwd_path.is_dir():
                return str(cwd_path)
        except (OSError, ValueError):
            pass
    # fallback
    try:
        return str(Path(os.getcwd()).resolve())
    except Exception:
        return os.getcwd()


@register_tool(name="run_shell_script",description="执行Shell脚本",parameters={"script":{"type":"string","description":"脚本内容"},"cwd":{"type":"string","description":"工作目录","default":""},"timeout":{"type":"integer","description":"超时秒数，默认120","default":120}},category="devops")
def run_shell_script(script: str, cwd: str = "", timeout: int = 120) -> dict:
    """执行 shell 脚本（支持多行），自动验证工作目录有效性"""
    resolved_cwd = _resolve_cwd(cwd)
    
    stdout, stderr, rc = _run_cmd_safe(script, cwd=resolved_cwd, timeout=timeout, shell=True)
    return {
        "success": rc == 0,
        "exit_code": rc,
        "stdout": stdout,
        "stderr": stderr
    }


@register_tool(name="deploy_pipeline",description="执行完整部署流水线(构建+安装)",parameters={"project_path":{"type":"string","description":"项目路径"},"build_type":{"type":"string","description":"构建类型","default":"android"}},category="devops")
def deploy_pipeline(project_path: str, build_type: str = "android") -> dict:
    """一键部署流水线：构建 → 安装 → 启动"""
    steps = []
    
    if build_type == "android":
        # Step 1: 构建
        build_result = gradle_build(project_path)
        steps.append({"step": "build", "result": build_result})
        
        if build_result["success"] and build_result["artifacts"]:
            apk_path = build_result["artifacts"][0]["path"]
            
            # Step 2: 安装到手机
            install_result = adb_install(apk_path)
            steps.append({"step": "install", "result": install_result})
            
            # Step 3: 截图验证
            if install_result["success"]:
                time.sleep(3)
                screenshot_result = adb_screenshot()
                steps.append({"step": "screenshot", "result": screenshot_result})
    
    return {
        "success": all(s["result"].get("success", False) for s in steps),
        "pipeline_type": build_type,
        "steps": steps
    }
