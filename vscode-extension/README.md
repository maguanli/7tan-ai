# 7Tan AI — VS Code 扩展

> 🎮 将 7Tan AI 助手集成到 VS Code，随时随地进行 AI 对话、代码审查、代码生成。

## 功能

| 功能 | 操作 | 快捷键 |
|------|------|--------|
| 🔍 **审查代码** | 右键选中代码 → 7Tan: 审查代码 | `Ctrl+Shift+R` |
| 📖 **解释代码** | 右键选中代码 → 7Tan: 解释代码 | `Ctrl+Shift+E` |
| 🚀 **优化代码** | 右键选中代码 → 7Tan: 优化代码 | - |
| 🧪 **生成测试** | 右键选中代码 → 7Tan: 生成测试 | - |
| ✨ **生成代码** | `Ctrl+Shift+P` → 7Tan: 生成代码 | - |
| 💬 **AI 对话** | 侧边栏 → 7Tan AI 面板 | - |

## 安装

1. 复制 `vscode-extension` 文件夹到 VS Code 扩展目录：
   - Windows: `%USERPROFILE%\.vscode\extensions\7tan.7tan-ai-1.0.0`
2. 重启 VS Code
3. 确保 7Tan 服务已启动（`localhost:9800`）

或通过 VS Code 命令面板：
- `Ctrl+Shift+P` → `Developer: Install Extension from Location...`
- 选择 `vscode-extension` 文件夹

## 依赖

- **7Tan 桌面应用** 必须运行中（提供 API 服务）
- VS Code 1.74+

## 配置

在 VS Code 设置中可修改：

```json
{
  "7tan.apiUrl": "http://localhost:9800",
  "7tan.autoStartServer": true
}
```
