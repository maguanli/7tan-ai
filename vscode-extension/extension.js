/**
 * 7Tan AI — VS Code 扩展入口
 * 
 * 功能：
 *  - 侧边栏 AI 对话面板
 *  - 右键菜单：审查代码 / 解释代码 / 优化代码 / 生成测试
 *  - 命令面板集成
 *  - 与本地 7Tan 服务 (localhost:9800) 通信
 */

const vscode = require('vscode');
const { SidebarProvider } = require('./src/sidebarProvider');
const { ApiClient } = require('./src/apiClient');

/** @type {SidebarProvider} */
let sidebarProvider = null;

/** @type {ApiClient} */
let apiClient = null;

/**
 * 扩展激活
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('🚀 7Tan AI 扩展已激活');

    // 初始化 API 客户端
    const config = vscode.workspace.getConfiguration('7tan');
    const apiUrl = config.get('apiUrl', 'http://localhost:9800');
    apiClient = new ApiClient(apiUrl);

    // ---- 注册侧边栏 ----
    sidebarProvider = new SidebarProvider(context.extensionUri, apiClient);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('7tan.sidebar', sidebarProvider)
    );

    // ---- 注册命令 ----
    // 打开对话
    context.subscriptions.push(
        vscode.commands.registerCommand('7tan.openChat', () => {
            vscode.commands.executeCommand('workbench.view.extension.7tan-sidebar');
        })
    );

    // 审查代码
    context.subscriptions.push(
        vscode.commands.registerCommand('7tan.reviewCode', async () => {
            await handleCodeAction('review', '请审查以下代码，找出潜在的安全漏洞、性能问题和代码异味，并给出改进建议：');
        })
    );

    // 解释代码
    context.subscriptions.push(
        vscode.commands.registerCommand('7tan.explainCode', async () => {
            await handleCodeAction('explain', '请详细解释以下代码的功能和实现原理：');
        })
    );

    // 优化代码
    context.subscriptions.push(
        vscode.commands.registerCommand('7tan.optimizeCode', async () => {
            await handleCodeAction('optimize', '请优化以下代码，提升性能和可读性，直接输出优化后的完整代码（用代码块包裹）：');
        })
    );

    // 生成测试
    context.subscriptions.push(
        vscode.commands.registerCommand('7tan.generateTests', async () => {
            await handleCodeAction('test', '请为以下代码生成完整的单元测试，覆盖边界条件和异常情况：');
        })
    );

    // 生成代码（无需选中）
    context.subscriptions.push(
        vscode.commands.registerCommand('7tan.generateCode', async () => {
            const description = await vscode.window.showInputBox({
                prompt: '请描述你想生成的代码',
                placeHolder: '例如：一个 Python Flask REST API，包含用户注册和登录',
                ignoreFocusOut: true
            });
            if (!description) return;
            await sendToSidebar(`请生成以下代码（直接输出完整可运行的代码，用代码块包裹）：\n${description}`);
        })
    );

    // 插入代码到编辑器
    context.subscriptions.push(
        vscode.commands.registerCommand('7tan.insertToEditor', (code) => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                editor.edit(editBuilder => {
                    editBuilder.replace(editor.selection, code);
                });
            }
        })
    );

    // ---- 状态栏 ----
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right, 100
    );
    statusBarItem.text = '$(hubot) 7Tan';
    statusBarItem.tooltip = '点击打开 7Tan AI 对话';
    statusBarItem.command = '7tan.openChat';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // 检查 7Tan 服务是否在线
    checkServerStatus(statusBarItem);
}

/**
 * 处理选中代码的操作
 * @param {string} action - 操作类型
 * @param {string} prompt - 提示词前缀
 */
async function handleCodeAction(action, prompt) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('请先打开一个文件');
        return;
    }

    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);

    if (!selectedText) {
        vscode.window.showWarningMessage('请先选中需要处理的代码');
        return;
    }

    const language = editor.document.languageId;
    const fileName = editor.document.fileName.split(/[/\\]/).pop();

    const fullPrompt = `${prompt}\n\n文件名: ${fileName}\n语言: ${language}\n\n\`\`\`${language}\n${selectedText}\n\`\`\``;

    await sendToSidebar(fullPrompt);
}

/**
 * 发送消息到侧边栏并显示
 * @param {string} message 
 */
async function sendToSidebar(message) {
    // 打开侧边栏
    await vscode.commands.executeCommand('workbench.view.extension.7tan-sidebar');

    // 发送消息到侧边栏
    if (sidebarProvider) {
        sidebarProvider.sendMessage(message);
    }
}

/**
 * 检查 7Tan 服务状态
 * @param {vscode.StatusBarItem} statusBarItem 
 */
async function checkServerStatus(statusBarItem) {
    try {
        const healthy = await apiClient.healthCheck();
        if (healthy) {
            statusBarItem.text = '$(hubot) 7Tan';
            statusBarItem.backgroundColor = undefined;
        } else {
            statusBarItem.text = '$(warning) 7Tan 离线';
            statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }
    } catch {
        statusBarItem.text = '$(warning) 7Tan 离线';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    }

    // 每 30 秒检查一次
    setInterval(async () => {
        try {
            const healthy = await apiClient.healthCheck();
            if (healthy) {
                statusBarItem.text = '$(hubot) 7Tan';
                statusBarItem.backgroundColor = undefined;
            } else {
                statusBarItem.text = '$(warning) 7Tan 离线';
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            }
        } catch {
            statusBarItem.text = '$(warning) 7Tan 离线';
            statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }
    }, 30000);
}

function deactivate() {
    console.log('👋 7Tan AI 扩展已停用');
}

module.exports = { activate, deactivate };
