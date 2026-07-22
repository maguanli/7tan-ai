"""
项目脚手架插件 — 快速创建项目模板、生成常见文件结构
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os


TEMPLATES = {
    "python-cli": {
        "description": "Python 命令行工具项目",
        "files": {
            "README.md": "# {name}\n\n{name} - Python CLI tool.\n\n## Install\n```bash\npip install -e .\n```\n\n## Usage\n```bash\n{name} --help\n```",
            "setup.py": """from setuptools import setup, find_packages

setup(
    name="{name}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={{
        "console_scripts": [
            "{name}={name}.cli:main",
        ],
    }},
    python_requires=">=3.8",
)""",
            "{name}/__init__.py": '"""\n{name} package\n"""\n__version__ = "0.1.0"',
            "{name}/cli.py": '"""\nCommand-line interface\n"""\nimport argparse\nimport sys\n\n\ndef main():\n    parser = argparse.ArgumentParser(description="CLI tool")\n    parser.add_argument("--version", action="version", version="0.1.0")\n    args = parser.parse_args()\n    print("Hello, World!")\n    return 0\n\n\nif __name__ == "__main__":\n    sys.exit(main())',
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\nvenv/\ndist/\nbuild/\n*.egg-info/\n.env",
        },
    },
    "python-web": {
        "description": "Python FastAPI Web 项目",
        "files": {
            "README.md": "# {name}\n\nFastAPI web application.\n\n## Run\n```bash\npip install -r requirements.txt\nuvicorn app.main:app --reload\n```",
            "requirements.txt": "fastapi>=0.100.0\nuvicorn[standard]\npydantic\npython-dotenv",
            "app/__init__.py": "",
            "app/main.py": '"""\n{name} - FastAPI Application\n"""\nfrom fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n\napp = FastAPI(title="{name}", version="0.1.0")\n\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=["*"],\n    allow_methods=["*"],\n    allow_headers=["*"],\n)\n\n\n@app.get("/")\nasync def root():\n    return {{"message": "Hello from {name}"}}\n\n\n@app.get("/health")\nasync def health():\n    return {{"status": "ok"}}',
            "app/models.py": '"""\nData models\n"""\nfrom pydantic import BaseModel\nfrom typing import Optional\nfrom datetime import datetime\n\n\nclass Item(BaseModel):\n    id: Optional[int] = None\n    name: str\n    created_at: datetime = datetime.now()',
            "app/routes.py": '"""\nAPI routes\n"""\nfrom fastapi import APIRouter\nfrom .models import Item\n\nrouter = APIRouter(prefix="/api")\n\n\n@router.get("/items")\nasync def list_items():\n    return []\n\n\n@router.post("/items")\nasync def create_item(item: Item):\n    return item',
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\nvenv/\n.env",
        },
    },
    "node-cli": {
        "description": "Node.js CLI 工具项目",
        "files": {
            "README.md": "# {name}\n\nNode.js CLI tool.\n\n## Install\n```bash\nnpm install\n```\n\n## Usage\n```bash\nnode index.js\n```",
            "package.json": '{\n  "name": "{name}",\n  "version": "0.1.0",\n  "description": "CLI tool",\n  "main": "index.js",\n  "scripts": {\n    "start": "node index.js"\n  },\n  "license": "MIT"\n}',
            "index.js": '#!/usr/bin/env node\n\nconst main = () => {\n  console.log("Hello, World!");\n};\n\nmain();',
            ".gitignore": "node_modules/\ndist/\n.env",
        },
    },
    "vue-app": {
        "description": "Vue 3 单页应用项目",
        "files": {
            "README.md": "# {name}\n\nVue 3 application.\n\n## Setup\n```bash\nnpm install\nnpm run dev\n```",
            "package.json": '{\n  "name": "{name}",\n  "version": "0.1.0",\n  "scripts": {\n    "dev": "vite",\n    "build": "vite build"\n  },\n  "dependencies": {\n    "vue": "^3.3.0"\n  },\n  "devDependencies": {\n    "@vitejs/plugin-vue": "^4.0.0",\n    "vite": "^4.0.0"\n  }\n}',
            "vite.config.js": 'import { defineConfig } from "vite";\nimport vue from "@vitejs/plugin-vue";\n\nexport default defineConfig({\n  plugins: [vue()],\n});',
            "index.html": '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n  <meta charset="UTF-8">\n  <title>{name}</title>\n</head>\n<body>\n  <div id="app"></div>\n  <script type="module" src="/src/main.js"></script>\n</body>\n</html>',
            "src/main.js": 'import { createApp } from "vue";\nimport App from "./App.vue";\n\ncreateApp(App).mount("#app");',
            "src/App.vue": '<template>\n  <div id="app">\n    <h1>{name}</h1>\n  </div>\n</template>\n\n<script>\nexport default {\n  name: "App",\n};\n</script>',
        },
    },
}


@register_tool(
    name="list_templates",
    description="列出所有可用的项目模板（Python CLI、FastAPI Web、Node.js CLI、Vue 3 等）。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="scaffold"
)
def list_templates() -> str:
    """列出可用模板"""
    lines = ["📦 可用项目模板:\n"]
    for name, info in TEMPLATES.items():
        file_count = len(info["files"])
        lines.append(f"  • {name:15s} — {info['description']} ({file_count} 文件)")
    return "\n".join(lines)


@register_tool(
    name="create_project",
    description="使用模板快速创建新项目。支持 python-cli/python-web/node-cli/vue-app 等模板。",
    parameters={
        "type": "object",
        "properties": {
            "template": {"type": "string", "description": "模板名称（使用 list_templates 查看可用模板）"},
            "name": {"type": "string", "description": "项目名称"},
            "path": {"type": "string", "description": "创建位置目录", "default": "."},
        },
        "required": ["template", "name"]
    },
    category="scaffold"
)
def create_project(template: str, name: str, path: str = ".") -> str:
    """创建项目脚手架"""
    if template not in TEMPLATES:
        return f"未知模板 '{template}'。可用: {', '.join(TEMPLATES.keys())}"

    project_dir = os.path.join(path, name)
    if os.path.exists(project_dir):
        return f"目录已存在: {project_dir}"

    info = TEMPLATES[template]
    created = []
    for rel_path, content in info["files"].items():
        # 替换 {name} 占位符
        formatted_path = rel_path.replace("{name}", name)
        formatted_content = content.replace("{name}", name)

        full_path = os.path.join(project_dir, formatted_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)
        created.append(f"  ✅ {formatted_path}")

    return (f"🎉 项目 '{name}' 已创建 (模板: {template})\n\n" + "\n".join(created))


@register_tool(
    name="generate_gitignore",
    description="根据项目类型生成 .gitignore 文件（Python/Node/Go/Rust/Vue 等）。",
    parameters={
        "type": "object",
        "properties": {
            "project_type": {"type": "string", "description": "项目类型: python/node/go/rust/vue/通用"},
            "path": {"type": "string", "description": "保存位置", "default": "."},
        },
        "required": ["project_type"]
    },
    category="scaffold"
)
def generate_gitignore(project_type: str, path: str = ".") -> str:
    """生成 .gitignore"""
    templates = {
        "python": "__pycache__/\n*.py[cod]\n*.egg-info/\ndist/\nbuild/\n.venv/\nvenv/\n.env\n*.log",
        "node": "node_modules/\ndist/\n.env\n*.log\nnpm-debug.log*",
        "go": "*.exe\n*.test\n*.out\nvendor/\n",
        "rust": "target/\n**/*.rs.bk\nCargo.lock\n",
        "vue": "node_modules/\ndist/\n.env\n*.log",
    }
    content = templates.get(project_type, templates["python"])
    filepath = os.path.join(path, ".gitignore")
    if os.path.exists(filepath):
        return f"⚠️ .gitignore 已存在，不会覆盖"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ .gitignore 已生成 ({project_type})"
