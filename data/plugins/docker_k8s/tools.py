
"""
Docker & K8s 管理插件 — 提供容器化和集群管理能力
"""
import subprocess
import json
import os
from pathlib import Path
from loguru import logger


def docker_ps(all_containers: bool = False) -> str:
    """列出 Docker 容器"""
    cmd = ["docker", "ps"]
    if all_containers:
        cmd.append("-a")
    cmd.extend(["--format", "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}\t{{.Ports}}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout
        return f"❌ Docker 命令失败: {result.stderr}"
    except FileNotFoundError:
        return "❌ Docker 未安装或未在 PATH 中"
    except Exception as e:
        return f"❌ 错误: {e}"


def docker_images() -> str:
    """列出 Docker 镜像"""
    cmd = ["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout
        return f"❌ Docker 命令失败: {result.stderr}"
    except FileNotFoundError:
        return "❌ Docker 未安装"
    except Exception as e:
        return f"❌ 错误: {e}"


def docker_compose_up(compose_file: str = "docker-compose.yml", detached: bool = True) -> str:
    """启动 docker-compose 服务"""
    path = Path(compose_file)
    if not path.exists():
        return f"❌ 文件不存在: {compose_file}"

    cmd = ["docker-compose", "-f", str(path), "up"]
    if detached:
        cmd.append("-d")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return f"✅ 服务已启动\n{result.stdout}"
        return f"❌ 启动失败: {result.stderr}"
    except Exception as e:
        return f"❌ 错误: {e}"


def docker_compose_down(compose_file: str = "docker-compose.yml") -> str:
    """停止 docker-compose 服务"""
    path = Path(compose_file)
    if not path.exists():
        return f"❌ 文件不存在: {compose_file}"

    cmd = ["docker-compose", "-f", str(path), "down"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return f"✅ 服务已停止\n{result.stdout}"
        return f"❌ 停止失败: {result.stderr}"
    except Exception as e:
        return f"❌ 错误: {e}"


def docker_logs(container_name: str, tail: int = 100) -> str:
    """查看容器日志"""
    cmd = ["docker", "logs", "--tail", str(tail), container_name]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout[-5000:]  # 限制输出
        return f"❌ 获取日志失败: {result.stderr}"
    except Exception as e:
        return f"❌ 错误: {e}"


def docker_build(dockerfile_dir: str = ".", tag: str = "app:latest") -> str:
    """构建 Docker 镜像"""
    path = Path(dockerfile_dir)
    if not path.exists():
        return f"❌ 目录不存在: {dockerfile_dir}"
    dockerfile = path / "Dockerfile"
    if not dockerfile.exists():
        return f"❌ 未找到 Dockerfile: {dockerfile}"

    cmd = ["docker", "build", "-t", tag, str(path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return f"✅ 镜像构建成功: {tag}\n{result.stdout[-2000:]}"
        return f"❌ 构建失败: {result.stderr[-2000:]}"
    except Exception as e:
        return f"❌ 错误: {e}"


def docker_prune() -> str:
    """清理未使用的 Docker 资源"""
    cmd = ["docker", "system", "prune", "-f"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return f"✅ 清理完成\n{result.stdout}"
        return f"❌ 清理失败: {result.stderr}"
    except Exception as e:
        return f"❌ 错误: {e}"


def kubectl_get(resource_type: str = "pods", namespace: str = "default") -> str:
    """获取 Kubernetes 资源（pods/services/deployments等）"""
    cmd = ["kubectl", "get", resource_type, "-n", namespace]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout
        return f"❌ kubectl 命令失败: {result.stderr}"
    except FileNotFoundError:
        return "❌ kubectl 未安装或未配置"
    except Exception as e:
        return f"❌ 错误: {e}"


def kubectl_apply(yaml_file: str, namespace: str = "default") -> str:
    """应用 Kubernetes YAML 配置"""
    path = Path(yaml_file)
    if not path.exists():
        return f"❌ 文件不存在: {yaml_file}"

    cmd = ["kubectl", "apply", "-f", str(path), "-n", namespace]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return f"✅ 配置已应用\n{result.stdout}"
        return f"❌ 应用失败: {result.stderr}"
    except Exception as e:
        return f"❌ 错误: {e}"


# 注册工具
def register(registry_func):
    registry_func(name="docker_ps", description="列出 Docker 容器（可选 all_containers=true 包括已停止的）",
                  parameters={"all_containers": {"type": "boolean", "description": "是否显示所有容器"}},
                  category="devops")(docker_ps)

    registry_func(name="docker_images", description="列出 Docker 镜像列表",
                  parameters={}, category="devops")(docker_images)

    registry_func(name="docker_compose_up", description="启动 docker-compose 服务",
                  parameters={
                      "compose_file": {"type": "string", "description": "docker-compose.yml 路径"},
                      "detached": {"type": "boolean", "description": "是否后台运行"}
                  }, category="devops")(docker_compose_up)

    registry_func(name="docker_compose_down", description="停止 docker-compose 服务",
                  parameters={"compose_file": {"type": "string", "description": "docker-compose.yml 路径"}},
                  category="devops")(docker_compose_down)

    registry_func(name="docker_logs", description="查看容器日志",
                  parameters={
                      "container_name": {"type": "string", "description": "容器名称"},
                      "tail": {"type": "integer", "description": "显示最后N行"}
                  }, category="devops")(docker_logs)

    registry_func(name="docker_build", description="构建 Docker 镜像",
                  parameters={
                      "dockerfile_dir": {"type": "string", "description": "Dockerfile 所在目录"},
                      "tag": {"type": "string", "description": "镜像标签"}
                  }, category="devops")(docker_build)

    registry_func(name="docker_prune", description="清理未使用的 Docker 资源（镜像/容器/网络）",
                  parameters={}, category="devops")(docker_prune)

    registry_func(name="kubectl_get", description="获取 Kubernetes 资源列表",
                  parameters={
                      "resource_type": {"type": "string", "description": "资源类型：pods/services/deployments/nodes"},
                      "namespace": {"type": "string", "description": "命名空间"}
                  }, category="devops")(kubectl_get)

    registry_func(name="kubectl_apply", description="应用 Kubernetes YAML 配置文件",
                  parameters={
                      "yaml_file": {"type": "string", "description": "YAML 文件路径"},
                      "namespace": {"type": "string", "description": "命名空间"}
                  }, category="devops")(kubectl_apply)
