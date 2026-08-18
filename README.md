# 7Tan 🎮

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)



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
git clone https://github.com/your-account/7tan-ai.git
cd 7tan
pip install -r requirements.txt
```

首次运行会自动进入 CLI 配置引导，设置 AI 模型、API Key、管理后台和云存储。

---

## 🔐 安全配置

项目不包含任何真实密钥。运行前请通过环境变量或配置文件设置：

| 变量 | 用途 |
|:--|:--|
| `DEEPSEEK_API_KEY` | DeepSeek 对话模型（`sk-` 开头）|
| `DB_PASS` | MySQL 数据库密码（server/ 目录 PHP 服务）|
| `OSS_ACCESS_KEY` / `OSS_SECRET_KEY` | 阿里云 OSS 存储密钥 |
| `VISION_KEY` | 智谱 GLM-4V 视觉模型密钥 |

参考 `.env.example` 获取完整变量列表。**切勿将真实密钥提交到仓库。**

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
├── .env.example             # 环境变量模板（含 API Key 等）
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

## 📄 License

[MIT](LICENSE) © 7Tan Project
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

*Made with ❤️ by 7Tan AI*
