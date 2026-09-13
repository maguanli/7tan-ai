# 🎮 7Tan — VS Code AI 智能编程助手 v2.0

> 一站式 AI DevOps 工具集：代码补全、AI 对话、代码审查、安全扫描、Git 操作、ADB 安装

---

## 🚀 快速安装

### 前置要求
- **Node.js** ≥ 18（下载: https://nodejs.org/）
- **VS Code** ≥ 1.80

### 方式一：一键安装（推荐）
```powershell
cd D:\7tan\7tanAI\extensions\vscode-7tan-copilot
.\install.bat
```

### 方式二：手动安装
```powershell
cd D:\7tan\7tanAI\extensions\vscode-7tan-copilot
npm install
npm run compile

# 然后在 VS Code 中:
# Ctrl+Shift+P → Developer: Install Extension from Location...
# 选择当前目录
```

### 方式三：打包安装
```powershell
npm install
npm install -g @vscode/vsce
npm run package
code --install-extension vscode-7tan-copilot-2.0.0.vsix
```

---

## ⚙️ 配置

安装后在 VS Code 中：
1. 按 `Ctrl+Shift+P` → `7Tan: 配置 API`
2. 输入 DeepSeek API Key（`sk-...`）或留空使用 7Tan 本地代理
3. 输入 7Tan 后端地址（默认 `http://127.0.0.1:17890`）

---

## ⌨️ 功能 & 快捷键

### 🧠 AI 代码补全
| 操作 | 说明 |
|------|------|
| 自动触发 | 输入代码后稍等，自动灰色补全 |
| `Tab` | 接受补全 |
| `Ctrl+Shift+P` → `7Tan: 切换代码补全` | 临时关闭 |

### 💬 AI 对话面板
| 操作 | 说明 |
|------|------|
| 侧边栏 | 点击左侧 7Tan 图标打开 |
| `Enter` | 发送消息 |
| `Shift+Enter` | 换行 |

### 🔍 代码审查 & 安全
| 快捷键 | 命令 | 说明 |
|------|------|------|
| - | `7Tan: AI 代码审查当前文件` | 全维度代码质量分析 |
| - | `7Tan: AI 代码审查当前目录` | 项目整体评估 |
| - | `7Tan: 安全扫描当前文件` | 漏洞检测 |

### ✨ AI 处理选中代码
| 快捷键 | 命令 | 说明 |
|------|------|------|
| `Ctrl+Shift+E` | `7Tan: AI 解释选中代码` | 解释逻辑 |
| `Ctrl+Shift+F` | `7Tan: AI 修复选中代码` | 自动修复 Bug |
| - | `7Tan: AI 优化选中代码` | 性能优化 |
| - | `7Tan: AI 添加注释` | 自动注释 |

右键菜单也可找到以上命令。

### 🔧 Git 操作
| 命令 | 说明 |
|------|------|
| `7Tan: AI 生成 Commit 信息` | 根据 diff 生成 Conventional Commits |
| `7Tan: Git 提交 (AI Commit Message)` | 自动生成 + 提交 |
| `7Tan: Git 推送` | push 到远程 |
| `7Tan: Git 提交历史` | 查看 log |

### 📱 ADB
| 命令 | 说明 |
|------|------|
| `7Tan: ADB 安装 APK` | 选择 APK 安装到设备 |

---

## 🎮 配合 7Tan 桌面应用

1. 启动 7Tan 桌面应用
2. VS Code 扩展自动检测 `localhost:17890`
3. 无需配置 API Key，直接使用

**独立使用**（不启动桌面应用）时需配置 DeepSeek API Key。

---

## 📁 文件结构

```
vscode-7tan-copilot/
├── package.json          # 扩展清单
├── tsconfig.json         # TS 配置
├── install.bat           # 一键安装脚本
├── src/
│   ├── extension.ts      # 主入口 + 激活
│   ├── completion.ts     # 行内代码补全
│   ├── chatPanel.ts      # 侧边栏 AI 对话
│   ├── client.ts         # HTTP 客户端
│   └── commands.ts       # 所有命令实现
├── media/
│   └── icon-sidebar.svg  # 侧边栏图标
├── out/                  # 编译输出 (npm run compile)
└── README.md
```

---

## 🆚 与 GitHub Copilot / Cloud Code 对比

| 能力 | 7Tan | Copilot | Cloud Code |
|------|:---:|:---:|:---:|
| 代码补全 | ✅ | ✅ | ✅ |
| AI 对话 | ✅ | ✅ | ✅ |
| 代码审查 | ✅ | ❌ | ❌ |
| 安全扫描 | ✅ | ❌ | ❌ |
| Git AI 提交 | ✅ | ❌ | ❌ |
| ADB 安装 | ✅ | ❌ | ❌ |
| K8s 管理 | ✅ | ❌ | ✅ |
| 免费（自带 Key） | ✅ | ❌ | ❌ |
