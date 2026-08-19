/**
 * 7Tan VS Code 扩展 — 主入口
 * 
 * 功能：
 *   - AI 代码补全（行内 InlineCompletion）
 *   - AI 对话面板（侧边栏 Chat）
 *   - AI 代码审查 & 安全扫描
 *   - AI 解释/修复/优化/注释选中代码
 *   - AI 生成 Commit 信息
 *   - Git 提交/推送/历史
 *   - ADB 安装 APK
 * 
 * 支持两种模式：
 *   1. 配合 7Tan 桌面应用（localhost:17890）
 *   2. 独立使用（配置 DeepSeek API Key）
 */

import * as vscode from 'vscode';
import { TanCompletionProvider } from './completion';
import { TanChatPanel } from './chatPanel';
import { getClient } from './client';
import * as cmd from './commands';

let chatPanelProvider: TanChatPanel;

export function activate(context: vscode.ExtensionContext) {

    console.log('🚀 7Tan AI 扩展已激活');

    // ── 1. 侧边栏 AI 对话面板 ──────────────────
    chatPanelProvider = new TanChatPanel(context.extensionUri);

    const chatViewRegistration = vscode.window.registerWebviewViewProvider(
        TanChatPanel.viewType,
        chatPanelProvider,
        { webviewOptions: { retainContextWhenHidden: true } }
    );

    // ── 2. 行内代码补全 ─────────────────────────
    const completionProvider = new TanCompletionProvider();

    const completionRegistration = vscode.languages.registerInlineCompletionItemProvider(
        { pattern: "**" },
        completionProvider
    );

    // ── 3. 注册所有命令 ─────────────────────────
    const commands = [
        vscode.commands.registerCommand('7tan.toggleCompletion', () => {
            const config = vscode.workspace.getConfiguration("7tan.completion");
            const current = config.get<boolean>("enabled", true);
            config.update("enabled", !current, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(
                `7Tan 代码补全: ${!current ? '✅ 已启用' : '⏸️ 已禁用'}`
            );
        }),

        vscode.commands.registerCommand('7tan.configure', cmd.configure),

        // 代码审查
        vscode.commands.registerCommand('7tan.codeReview', cmd.codeReview),
        vscode.commands.registerCommand('7tan.codeReviewFolder', cmd.codeReviewFolder),
        vscode.commands.registerCommand('7tan.securityScan', cmd.securityScan),

        // 选中代码处理
        vscode.commands.registerCommand('7tan.explainCode', cmd.explainCode),
        vscode.commands.registerCommand('7tan.fixCode', cmd.fixCode),
        vscode.commands.registerCommand('7tan.optimizeCode', cmd.optimizeCode),
        vscode.commands.registerCommand('7tan.addComment', cmd.addComment),

        // Git
        vscode.commands.registerCommand('7tan.generateCommitMsg', cmd.generateCommitMsg),
        vscode.commands.registerCommand('7tan.gitCommit', cmd.gitCommit),
        vscode.commands.registerCommand('7tan.gitPush', cmd.gitPush),
        vscode.commands.registerCommand('7tan.gitLog', cmd.gitLog),

        // ADB
        vscode.commands.registerCommand('7tan.adbInstall', cmd.adbInstall),

        // 打开对话
        vscode.commands.registerCommand('7tan.openChat', () => {
            vscode.commands.executeCommand('7tan.chatView.focus');
        }),
    ];

    // ── 4. 状态栏 ───────────────────────────────
    const statusBar = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right, 100
    );
    statusBar.text = "$(sparkle) 7Tan";
    statusBar.tooltip = "7Tan AI — 点击切换代码补全";
    statusBar.command = "7tan.toggleCompletion";
    statusBar.show();

    // ── 5. 启动时检测后端 ────────────────────────
    checkBackend();

    // ── 注册所有订阅 ─────────────────────────────
    context.subscriptions.push(
        chatViewRegistration,
        completionRegistration,
        statusBar,
        ...commands
    );

    console.log('✅ 7Tan AI 扩展初始化完成');
}

export function deactivate() {
    console.log('👋 7Tan AI 扩展已停用');
}

/** 异步检测后端状态 */
async function checkBackend() {
    const client = getClient();
    try {
        const isOnline = await client.ping();
        if (isOnline) {
            vscode.window.showInformationMessage('✅ 7Tan AI 已连接到本地后端');
        }
    } catch {
        // 静默处理，后端可能未启动
        console.log('7Tan 后端未运行，将使用直连模式');
    }
}
