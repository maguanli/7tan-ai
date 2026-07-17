
"""
Docker & K8s 管理插件 — 完整的容器化和集群管理能力 (v2.0)
覆盖 Cloud Code 全部核心 K8s 功能
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import subprocess
import json
import os
from loguru import logger


# ============================================================
# Docker 部分 (保留原有)
# ============================================================

@register_tool(name="docker_ps", description="列出 Docker 容器（可选 all_containers=true 包括已停止的）", parameters={"all_containers": {"type": "boolean", "description": "是否显示所有容器"}}, category="devops")
def docker_ps(all_containers: bool = False) -> str:
    cmd = ["docker", "ps"] + (["-a"] if all_containers else []) + ["--format", "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}\t{{.Ports}}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout if r.returncode == 0 else f"❌ {r.stderr}"
    except FileNotFoundError:
        return "❌ Docker 未安装"
    except Exception as e:
        return f"❌ {e}"


@register_tool(name="docker_images", description="列出 Docker 镜像列表", parameters={}, category="devops")
def docker_images() -> str:
    try:
        r = subprocess.run(["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"], capture_output=True, text=True, timeout=15)
        return r.stdout if r.returncode == 0 else f"❌ {r.stderr}"
    except FileNotFoundError:
        return "❌ Docker 未安装"
    except Exception as e:
        return f"❌ {e}"


@register_tool(name="docker_compose_up", description="启动 docker-compose 服务", parameters={"compose_file": {"type": "string", "description": "docker-compose.yml 路径"}, "detached": {"type": "boolean", "description": "是否后台运行"}}, category="devops")
def docker_compose_up(compose_file: str = "docker-compose.yml", detached: bool = True) -> str:
    p = Path(compose_file)
    if not p.exists(): return f"❌ 文件不存在: {compose_file}"
    try:
        r = subprocess.run(["docker-compose", "-f", str(p), "up"] + (["-d"] if detached else []), capture_output=True, text=True, timeout=60)
        return f"✅ 已启动\n{r.stdout}" if r.returncode == 0 else f"❌ {r.stderr}"
    except Exception as e:
        return f"❌ {e}"


@register_tool(name="docker_compose_down", description="停止 docker-compose 服务", parameters={"compose_file": {"type": "string", "description": "docker-compose.yml 路径"}}, category="devops")
def docker_compose_down(compose_file: str = "docker-compose.yml") -> str:
    p = Path(compose_file)
    if not p.exists(): return f"❌ 文件不存在: {compose_file}"
    try:
        r = subprocess.run(["docker-compose", "-f", str(p), "down"], capture_output=True, text=True, timeout=60)
        return f"✅ 已停止\n{r.stdout}" if r.returncode == 0 else f"❌ {r.stderr}"
    except Exception as e:
        return f"❌ {e}"


@register_tool(name="docker_logs", description="查看容器日志", parameters={"container_name": {"type": "string", "description": "容器名称"}, "tail": {"type": "integer", "description": "显示最后N行"}}, category="devops")
def docker_logs(container_name: str, tail: int = 100) -> str:
    try:
        r = subprocess.run(["docker", "logs", "--tail", str(tail), container_name], capture_output=True, text=True, timeout=15)
        return r.stdout[-5000:] if r.returncode == 0 else f"❌ {r.stderr}"
    except Exception as e:
        return f"❌ {e}"


@register_tool(name="docker_build", description="构建 Docker 镜像", parameters={"dockerfile_dir": {"type": "string", "description": "Dockerfile 所在目录"}, "tag": {"type": "string", "description": "镜像标签"}}, category="devops")
def docker_build(dockerfile_dir: str = ".", tag: str = "app:latest") -> str:
    p = Path(dockerfile_dir)
    if not p.exists(): return f"❌ 目录不存在: {dockerfile_dir}"
    if not (p / "Dockerfile").exists(): return f"❌ 未找到 Dockerfile"
    try:
        r = subprocess.run(["docker", "build", "-t", tag, str(p)], capture_output=True, text=True, timeout=300)
        return f"✅ 构建成功: {tag}\n{r.stdout[-2000:]}" if r.returncode == 0 else f"❌ {r.stderr[-2000:]}"
    except Exception as e:
        return f"❌ {e}"


@register_tool(name="docker_prune", description="清理未使用的 Docker 资源（镜像/容器/网络）", parameters={}, category="devops")
def docker_prune() -> str:
    try:
        r = subprocess.run(["docker", "system", "prune", "-f"], capture_output=True, text=True, timeout=60)
        return f"✅ 清理完成\n{r.stdout}" if r.returncode == 0 else f"❌ {r.stderr}"
    except Exception as e:
        return f"❌ {e}"


# ============================================================
# K8s v2.0 — 补齐 Cloud Code 全部核心能力 (17项新增)
# ============================================================

@register_tool(name='kubectl_get', description='获取 Kubernetes 资源列表：pods/services/deployments/nodes/configmaps/secrets/namespaces/ingresses/pv/pvc/events', parameters={'resource_type': {'type': 'string', 'description': '资源类型'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_get(resource_type: str = 'pods', namespace: str = 'default') -> str:
    cmd = ['kubectl', 'get', resource_type, '-n', namespace]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout if r.returncode == 0 else f'❌ kubectl 失败: {r.stderr}'
    except FileNotFoundError:
        return '❌ kubectl 未安装或未配置'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_apply', description='应用 Kubernetes YAML 配置文件', parameters={'yaml_file': {'type': 'string', 'description': 'YAML 文件路径'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_apply(yaml_file: str, namespace: str = 'default') -> str:
    p = Path(yaml_file)
    if not p.exists(): return f'❌ 文件不存在: {yaml_file}'
    try:
        r = subprocess.run(['kubectl', 'apply', '-f', str(p), '-n', namespace], capture_output=True, text=True, timeout=30)
        return f'✅ 已应用\n{r.stdout}' if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_logs', description='查看 Pod 日志（支持 -f 持续输出时自动限制行数）', parameters={'pod_name': {'type': 'string', 'description': 'Pod 名称'}, 'namespace': {'type': 'string', 'description': '命名空间'}, 'container': {'type': 'string', 'description': '容器名（可选）'}, 'tail': {'type': 'integer', 'description': '最后N行'}}, category='devops')
def kubectl_logs(pod_name: str, namespace: str = 'default', container: str = '', tail: int = 200) -> str:
    cmd = ['kubectl', 'logs', pod_name, '-n', namespace, '--tail', str(tail)]
    if container: cmd += ['-c', container]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return r.stdout[-8000:] if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_exec', description='在 Pod 容器内执行命令（类似 docker exec）', parameters={'pod_name': {'type': 'string', 'description': 'Pod 名称'}, 'command': {'type': 'string', 'description': '要执行的命令'}, 'namespace': {'type': 'string', 'description': '命名空间'}, 'container': {'type': 'string', 'description': '容器名（可选）'}}, category='devops')
def kubectl_exec(pod_name: str, command: str, namespace: str = 'default', container: str = '') -> str:
    cmd = ['kubectl', 'exec', pod_name, '-n', namespace]
    if container: cmd += ['-c', container]
    cmd += ['--'] + command.split()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_describe', description='查看资源详细信息（describe），支持 pod/service/deployment/node 等', parameters={'resource_type': {'type': 'string', 'description': '资源类型: pod/service/deployment/node/ingress'}, 'resource_name': {'type': 'string', 'description': '资源名称'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_describe(resource_type: str, resource_name: str, namespace: str = 'default') -> str:
    cmd = ['kubectl', 'describe', resource_type, resource_name, '-n', namespace]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout[-8000:] if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_events', description='查看集群事件（可按命名空间过滤）', parameters={'namespace': {'type': 'string', 'description': '命名空间（留空=所有）'}}, category='devops')
def kubectl_events(namespace: str = '') -> str:
    cmd = ['kubectl', 'get', 'events'] + (['-n', namespace] if namespace else ['--all-namespaces']) + ['--sort-by=.metadata.creationTimestamp']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout[-6000:] if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_top', description='查看资源使用情况（CPU/内存），支持 pods/nodes', parameters={'resource_type': {'type': 'string', 'description': 'pods 或 nodes'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_top(resource_type: str = 'pods', namespace: str = 'default') -> str:
    cmd = ['kubectl', 'top', resource_type, '-n', namespace]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_context', description='查看/切换 kubectl 上下文（集群/用户/命名空间）', parameters={'action': {'type': 'string', 'description': 'list（查看所有上下文）/ current（当前）/ use:上下文名（切换）'}}, category='devops')
def kubectl_context(action: str = 'list') -> str:
    try:
        if action == 'list':
            r = subprocess.run(['kubectl', 'config', 'get-contexts'], capture_output=True, text=True, timeout=10)
        elif action == 'current':
            r = subprocess.run(['kubectl', 'config', 'current-context'], capture_output=True, text=True, timeout=10)
        elif action.startswith('use:'):
            ctx = action.split(':', 1)[1]
            r = subprocess.run(['kubectl', 'config', 'use-context', ctx], capture_output=True, text=True, timeout=10)
        else:
            return f'❌ 无效 action: {action}，请用 list/current/use:名称'
        return r.stdout if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_delete', description='删除 Kubernetes 资源', parameters={'resource_type': {'type': 'string', 'description': '资源类型: pod/service/deployment/namespace 等'}, 'resource_name': {'type': 'string', 'description': '资源名称'}, 'namespace': {'type': 'string', 'description': '命名空间'}, 'force': {'type': 'boolean', 'description': '是否强制删除'}}, category='devops')
def kubectl_delete(resource_type: str, resource_name: str, namespace: str = 'default', force: bool = False) -> str:
    cmd = ['kubectl', 'delete', resource_type, resource_name, '-n', namespace]
    if force: cmd.append('--force')
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return f'✅ 已删除\n{r.stdout}' if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_scale', description='扩缩容 Deployment/StatefulSet', parameters={'resource_type': {'type': 'string', 'description': 'deployment 或 statefulset'}, 'resource_name': {'type': 'string', 'description': '资源名称'}, 'replicas': {'type': 'integer', 'description': '副本数'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_scale(resource_type: str, resource_name: str, replicas: int, namespace: str = 'default') -> str:
    cmd = ['kubectl', 'scale', resource_type, resource_name, '--replicas', str(replicas), '-n', namespace]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return f'✅ 已扩缩容至 {replicas}\n{r.stdout}' if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_rollout', description='管理滚动更新：status/history/restart/undo', parameters={'action': {'type': 'string', 'description': 'status/history/restart/undo'}, 'resource_type': {'type': 'string', 'description': 'deployment 或 daemonset 等'}, 'resource_name': {'type': 'string', 'description': '资源名称'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_rollout(action: str, resource_type: str = 'deployment', resource_name: str = '', namespace: str = 'default') -> str:
    cmd = ['kubectl', 'rollout', action, f'{resource_type}/{resource_name}', '-n', namespace]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_port_forward', description='端口转发：将本地端口转发到 Pod 端口', parameters={'pod_name': {'type': 'string', 'description': 'Pod 名称'}, 'local_port': {'type': 'integer', 'description': '本地端口'}, 'pod_port': {'type': 'integer', 'description': 'Pod 端口'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_port_forward(pod_name: str, local_port: int, pod_port: int, namespace: str = 'default') -> str:
    cmd = ['kubectl', 'port-forward', f'{pod_name}', f'{local_port}:{pod_port}', '-n', namespace]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        import time; time.sleep(1)
        if proc.poll() is None:
            return f'✅ 端口转发已启动: localhost:{local_port} -> {pod_name}:{pod_port} (进程PID: {proc.pid})'
        else:
            return f'❌ 端口转发启动失败: {proc.stderr.read()}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_create_ns', description='创建命名空间', parameters={'namespace': {'type': 'string', 'description': '命名空间名称'}}, category='devops')
def kubectl_create_ns(namespace: str) -> str:
    try:
        r = subprocess.run(['kubectl', 'create', 'namespace', namespace], capture_output=True, text=True, timeout=15)
        return f'✅ 命名空间已创建: {namespace}\n{r.stdout}' if r.returncode == 0 else f'❌ {r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_dry_run', description='YAML 验证：对配置文件执行 --dry-run=client 语法检查', parameters={'yaml_file': {'type': 'string', 'description': 'YAML 文件路径'}, 'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_dry_run(yaml_file: str, namespace: str = 'default') -> str:
    p = Path(yaml_file)
    if not p.exists(): return f'❌ 文件不存在: {yaml_file}'
    try:
        r = subprocess.run(['kubectl', 'apply', '-f', str(p), '--dry-run=client', '-n', namespace], capture_output=True, text=True, timeout=15)
        return f'✅ YAML 语法正确\n{r.stdout}' if r.returncode == 0 else f'❌ YAML 错误:\n{r.stderr}'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_config_view', description='查看 kubeconfig 配置（集群/用户/上下文信息，敏感字段已脱敏）', parameters={}, category='devops')
def kubectl_config_view() -> str:
    try:
        r = subprocess.run(['kubectl', 'config', 'view'], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return f'❌ {r.stderr}'
        sanitized = re.sub(r'(client-certificate-data:\s*).*', r'\1***REDACTED***', r.stdout)
        sanitized = re.sub(r'(client-key-data:\s*).*', r'\1***REDACTED***', sanitized)
        sanitized = re.sub(r'(token:\s*).*', r'\1***REDACTED***', sanitized)
        return sanitized[-6000:]
    except FileNotFoundError:
        return '❌ kubectl 未安装或未配置'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='helm_list', description='列出 Helm 已安装的 Release', parameters={'namespace': {'type': 'string', 'description': '命名空间（留空=所有）'}}, category='devops')
def helm_list(namespace: str = '') -> str:
    cmd = ['helm', 'list'] + (['-n', namespace] if namespace else ['--all-namespaces'])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout if r.returncode == 0 else f'❌ {r.stderr}'
    except FileNotFoundError:
        return '❌ Helm 未安装'
    except Exception as e:
        return f'❌ {e}'


@register_tool(name='kubectl_get_all', description='一键查看命名空间下所有资源（pod/svc/deploy/ingress/configmap/secret/pvc）', parameters={'namespace': {'type': 'string', 'description': '命名空间'}}, category='devops')
def kubectl_get_all(namespace: str = 'default') -> str:
    result = []
    for rt in ['pods', 'services', 'deployments', 'ingresses', 'configmaps', 'secrets', 'pvc']:
        r = subprocess.run(['kubectl', 'get', rt, '-n', namespace], capture_output=True, text=True, timeout=10)
        result.append(f'=== {rt.upper()} ===\n{r.stdout if r.returncode == 0 else "N/A"}')
    return '\n'.join(result)
