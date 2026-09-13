# 7Tan 🎮

[![CI](https://github.com/your-org/7tan/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/7tan/actions/workflows/ci.yml)

<!-- CI Badge：推送仓库到 GitHub 后，把 your-org/7tan 替换为实际 owner/repo 即可显示构建状态 -->

> **7坛 AI 小编「盘古」** — 游戏内容自动化发布平台

7Tan 是一个智能游戏编辑系统，能自动从游戏源站采集信息、撰写专业评测、翻译介绍、上传云存储，并一键发布到 7坛管理后台。

---

## ✨ 核心能力

| 功能 | 说明 |
|:--|:--|
| 🌐 智能采集 | 自动浏览游戏源站，提取详情、截图、下载链接 |
| ✍️ AI 撰写 | 深度分析 + HTML 游戏简介，支持英译中 |
| 📤 一键发布 | OSS 上传 + 7坛后台自动填表发布 |
| 💬 对话界面 | PyQt6 聊天式交互，Markdown 渲染、流式输出、思考过程 |
| 🧩 插件系统 | 47 插件、249 工具，热插拔扩展 |

---

## 🏗️ 技术栈

- **语言**: Python 3.11+
- **UI**: PyQt6
- **AI**: DeepSeek / OpenAI 兼容 API
- **数据库**: SQLite (SQLAlchemy ORM)
- **云存储**: 阿里云 OSS / 腾讯云 COS / 七牛 Kodo
- **构建**: PyInstaller

---

## 📦 安装

```bash
git clone https://github.com/your-org/7tan.git
cd 7tan
pip install -r requirements.txt
```

首次运行会自动进入 CLI 配置引导，设置 AI 模型、API Key、管理后台和云存储。

---

## 🚀 使用

```bash
python main.py
```

启动后进入对话界面，直接告诉 AI 你想做什么：

- "帮我发布 Steam 上的 Stardew Valley"
- "对比一下 Hollow Knight 和 Ori"
- "抓取 TapTap 首页新游"

---

## 📁 项目结构

```
7tan/
├── main.py                  # 入口
├── config.yaml              # 全局配置
├── src/
│   ├── agent/               # AI Agent 核心 (prompts, agent_loop, api)
│   ├── plugins/             # 插件管理器 (47 插件)
│   ├── ui/                  # PyQt6 界面 (chat_page, sidebar, settings)
│   │   ├── widgets/         # 独立 UI 组件
│   │   └── workers/         # 后台线程
│   ├── database/            # ORM 模型 + CRUD
│   ├── config/              # 配置管理 + 加密
│   └── utils/               # 工具函数
├── data/
│   ├── plugins/             # 插件注册清单
│   └── prompts/             # 提示词模板
├── dist/                    # PyInstaller 构建输出
├── downloads/               # 下载缓存
└── requirements.txt
```

---

## 🔧 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 构建
python build.bat
```

### 分支策略

- `master` — 稳定发布
- `develop` — 开发集成
- `feature/*` — 新功能分支

---

## 📊 项目规模

| 指标 | 数值 |
|:--|:--|
| Python 文件 | 116 (src)
| 总行数 | ~37,800 |
| 插件数 | 47 |
| 工具数 | 249 |
| 数据库表 | 12 |
| API 端点 | 31 |

---

*Made with ❤️ by 盘古 AI*
