# 7Tan AI 🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **7Tan AI「盘古」** — 会自己改代码、自我进化升级的 AI 编程工具平台

7Tan AI 是一个基于大语言模型的自进化 AI 工具平台：它能写代码、改代码、重构项目、自动构建重启，也能写作爆款文章、管理内容、自动化办公。核心能力是**编程辅助与自我升级**——你给它一个任务，它会调用 200+ 内置工具完成，甚至能修改自己的源码、重新打包、重启生效。

🌐 **官方网站/社区：https://www.7tan.com/bbs/**

---

## ✨ 核心能力

| 功能 | 说明 |
|:--|:--|
| 💻 AI 编程助手 | 写代码、补全、重构、代码审查、自动修 bug、跑测试、构建发布 |
| 🧬 自我进化升级 | AI 可以修改自身源码 → 重新构建 → 自动重启，持续自我迭代 |
| 🧩 插件系统 | 47 插件、249 工具，支持热插拔、动态创建新插件扩展能力 |
| 🎭 多智能体 | 采集 / 改写 / 审核 / 发布 多角色流水线协作 |
| ✍️ 爆款写作 | 选题生成、标题生成、大纲、正文撰写、质检，公众号一键发布 |
| 📊 桌面自动化 | 操作微信/浏览器/屏幕，OCR 识别、模板匹配、自动点击 |
| 🎮 内容自动化 | 游戏/软件资源采集、评测撰写、OSS 上传、自动发布 |
| 📈 数据分析 | 龙头识别、情绪周期、MACD 买卖点、每日复盘 |
| 🏛️ 传统文化 | 易经占卦、孙子兵法、每日一卦/兵法 |

---

## 🏗️ 技术栈

- **语言**: Python 3.11+
- **UI**: PyQt6 / Web 控制台
- **AI**: DeepSeek / 小米 MiMo / OpenAI 兼容 API / 智谱 GLM-4V 视觉
- **数据库**: SQLite (SQLAlchemy ORM)
- **云存储**: 阿里云 OSS / 腾讯云 COS / 七牛 Kodo
- **构建**: PyInstaller / rebuild.bat

---

## 📦 安装

```bash
git clone https://github.com/maguanli/7tan-ai.git
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

- "帮我重构 src/ 里的爬虫模块，加上重试机制"
- "写一个批量重命名文件的工具"
- "生成10个爆款公众号选题"
- "检查代码里的安全漏洞"

---

## 📁 项目结构

```
7tan/
├── main.py              # 主入口（桌面版）
├── web_main.py          # Web 控制台入口
├── src/                 # 核心源码
├── server/              # PHP 服务端
├── extensions/          # 扩展
├── mobile/              # 移动端
├── www/                 # Web 前端
├── docs/                # 文档
└── tests/               # 测试
```

---

## 🧬 自我进化示例

7Tan AI 不止是工具，它还能进化自己：

1. 告诉它：「帮我加一个批量压缩图片的插件」
2. AI 自动编写插件代码 → 注册到系统 → 重启生效
3. 下次对话直接可用新能力

这就是 7Tan AI 的核心理念：**AI 不只是被使用，而是可以持续升级自己。**

---

## 📄 License

[MIT](LICENSE) © 7tan.com

🌐 **https://www.7tan.com/bbs/** — 欢迎来社区交流、反馈、贡献代码
