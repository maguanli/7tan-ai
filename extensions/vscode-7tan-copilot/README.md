# 7Tan Copilot — VS Code 扩展

## 🚀 快速安装

### 方法一：一键安装（推荐）
```powershell
cd D:\7tan\7tanAI\extensions\vscode-7tan-copilot
npm install
npm run compile
```

然后在 VS Code 中：
1. 按 `Ctrl+Shift+P` → 输入 `Developer: Install Extension from Location...`
2. 选择 `D:\7tan\7tanAI\extensions\vscode-7tan-copilot`

### 方法二：打包安装
```powershell
cd D:\7tan\7tanAI\extensions\vscode-7tan-copilot
npm install
npm install -g @vscode/vsce
vsce package
code --install-extension vscode-7tan-copilot-1.0.0.vsix
```

## ⚙️ 配置

安装后在 VS Code 中：
1. 按 `Ctrl+Shift+P` → `7Tan Copilot: 配置 API`
2. 输入 DeepSeek API Key（`sk-...`）
3. 或者留空，配合 7Tan 桌面应用使用

## 🎮 配合 7Tan 桌面应用使用

1. 启动 7Tan 桌面应用
2. 在 7Tan 中启动代码补全服务
3. VS Code 扩展会自动通过 `localhost:17890` 连接

## ⌨️ 使用

在 VS Code 中编辑代码时：
- 输入代码后稍等片刻，AI 会自动给出补全建议（灰色文字）
- 按 `Tab` 接受补全
- 按 `Ctrl+Shift+P` → `7Tan Copilot: 切换开/关` 临时关闭

## 📁 文件结构
```
vscode-7tan-copilot/
├── package.json          # 扩展配置
├── tsconfig.json         # TypeScript 配置
├── src/
│   └── extension.ts      # 扩展主代码
├── out/                  # 编译输出（npm run compile 后生成）
└── README.md
```
