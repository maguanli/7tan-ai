"""
CI/CD 助手 — 生成 CI 配置、自动化发布日志、版本管理
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os


CI_TEMPLATES = {
    "github-python": {
        "file": ".github/workflows/ci.yml",
        "content": """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run tests
      run: pytest --cov=src --cov-report=xml
    - name: Lint
      run: pip install flake8 && flake8 src/ --max-line-length=120
""",
    },
    "github-node": {
        "file": ".github/workflows/ci.yml",
        "content": """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]

    steps:
    - uses: actions/checkout@v4
    - name: Use Node.js ${{ matrix.node-version }}
      uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'
    - run: npm ci
    - run: npm test
    - run: npm run lint
""",
    },
    "github-docker": {
        "file": ".github/workflows/docker.yml",
        "content": """name: Docker Build & Push

on:
  push:
    branches: [main, master]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        push: true
        tags: ${{ secrets.DOCKER_USERNAME }}/app:latest
""",
    },
}


@register_tool(
    name="generate_ci_config",
    description="为项目生成 CI/CD 配置文件（GitHub Actions / GitLab CI）。支持 Python、Node.js、Docker 等。",
    parameters={
        "type": "object",
        "properties": {
            "ci_type": {"type": "string", "description": "CI 模板: github-python/github-node/github-docker"},
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": ["ci_type"]
    },
    category="cicd"
)
def generate_ci_config(ci_type: str, project_root: str = ".") -> str:
    """生成 CI 配置"""
    if ci_type not in CI_TEMPLATES:
        return f"未知 CI 类型: {ci_type}。可用: {', '.join(CI_TEMPLATES.keys())}"

    tmpl = CI_TEMPLATES[ci_type]
    filepath = os.path.join(project_root, tmpl["file"])
    if os.path.exists(filepath):
        return f"⚠️ 配置文件已存在: {filepath}。不会覆盖。"

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(tmpl["content"])
    return f"✅ CI 配置已生成: {filepath}"


@register_tool(
    name="generate_changelog",
    description="根据 Git 提交历史自动生成 CHANGELOG.md，按版本和类型分组。支持 Conventional Commits 格式。",
    parameters={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径", "default": "."},
            "version": {"type": "string", "description": "版本号，如 v1.2.0", "default": ""},
        },
        "required": []
    },
    category="cicd"
)
def generate_changelog(repo_path: str = ".", version: str = "") -> str:
    """生成 CHANGELOG"""
    import subprocess
    git = None
    for g in ["git", "C:\\Program Files\\Git\\bin\\git.exe"]:
        try:
            r = subprocess.run([g, "--version"], capture_output=True, timeout=3,
                              creationflags=subprocess.CREATE_NO_WINDOW)
            if r.returncode == 0:
                git = g
                break
        except Exception:
            pass
    if not git:
        return "未找到 Git"

    # 获取最近标签
    try:
        r = subprocess.run([git, "-C", repo_path, "describe", "--tags", "--abbrev=0"],
                          capture_output=True, text=True, timeout=5,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        last_tag = r.stdout.strip()
    except Exception:
        last_tag = "HEAD~50"

    # 获取提交日志
    try:
        r = subprocess.run([git, "-C", repo_path, "log", "--oneline",
                           f"{last_tag}..HEAD" if last_tag else "-50"],
                          capture_output=True, text=True, timeout=10,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        commits = r.stdout.strip().split("\n") if r.stdout.strip() else []
    except Exception:
        commits = []

    # 分类
    features, fixes, chores, docs = [], [], [], []
    for c in commits:
        msg = c[c.index(" ") + 1:] if " " in c else c
        m = msg.lower()
        if m.startswith(("feat", "add", "新增")):
            features.append(f"- {msg}")
        elif m.startswith(("fix", "修复", "bug")):
            fixes.append(f"- {msg}")
        elif m.startswith(("doc", "文档")):
            docs.append(f"- {msg}")
        else:
            chores.append(f"- {msg}")

    lines = [f"# Changelog\n", f"## {version or 'Unreleased'} ({_date()})\n"]
    if features:
        lines.append("### ✨ 新功能\n" + "\n".join(features) + "\n")
    if fixes:
        lines.append("### 🐛 修复\n" + "\n".join(fixes) + "\n")
    if docs:
        lines.append("### 📖 文档\n" + "\n".join(docs) + "\n")
    if chores:
        lines.append("### 🔧 杂项\n" + "\n".join(chores) + "\n")
    return "\n".join(lines)


@register_tool(
    name="bump_version",
    description="自动升级项目版本号（语义化版本）。支持 patch/minor/major，自动更新 setup.py/package.json/pyproject.toml。",
    parameters={
        "type": "object",
        "properties": {
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
            "bump": {"type": "string", "description": "升级类型: patch/minor/major", "default": "patch"},
        },
        "required": []
    },
    category="cicd"
)
def bump_version(project_root: str = ".", bump: str = "patch") -> str:
    """升级版本号"""
    import re

    files_to_check = ["setup.py", "pyproject.toml", "package.json", "Cargo.toml"]
    updated = []

    for fname in files_to_check:
        fpath = os.path.join(project_root, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r") as f:
                content = f.read()
        except Exception:
            continue

        # 查找并升级版本号
        version_pattern = r'version\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']'
        m = re.search(version_pattern, content)
        if not m:
            continue

        major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if bump == "major":
            major += 1; minor = 0; patch = 0
        elif bump == "minor":
            minor += 1; patch = 0
        else:
            patch += 1

        new_version = f'{major}.{minor}.{patch}'
        new_content = content[:m.start()] + content[m.start():m.end()].replace(
            m.group(0), f'version = "{new_version}"'.replace('version =', m.group(0).split('=')[0] + '=')
        ) + content[m.end():]

        with open(fpath, "w") as f:
            f.write(new_content)
        updated.append(f"{fname}: {m.group(1)}.{m.group(2)}.{m.group(3)} → {new_version}")

    return "\n".join(updated) if updated else "未找到版本信息文件"


def _date():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")
