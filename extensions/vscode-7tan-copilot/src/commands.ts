/**
 * 7Tan 命令实现 — AI 代码审查、安全扫描、Git 操作等
 */

import * as vscode from 'vscode';
import * as child_process from 'child_process';
import { getClient, TanClient } from './client';
import { TanChatPanel } from './chatPanel';

// ── 代码审查 ──────────────────────────────────────

export async function codeReview() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('请先打开一个文件');
        return;
    }

    const code = editor.document.getText();
    const language = editor.document.languageId;
    const fileName = editor.document.uri.fsPath.split(/[\\/]/).pop() || '';

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `7Tan: 正在审查 ${fileName}...`,
        cancellable: true
    }, async (progress, token) => {
        const client = getClient();
        const prompt = `请对以下代码进行全面审查，从以下维度分析：
1. 🐛 **Bug 风险** — 潜在的空指针、边界条件、逻辑错误
2. 🔒 **安全问题** — SQL注入、XSS、硬编码密钥等
3. 📐 **代码结构** — 函数是否过长、圈复杂度、重复代码
4. ⚡ **性能问题** — 不必要的循环、内存泄漏风险
5. 📝 **可维护性** — 命名规范、注释质量、模块耦合度

语言: ${language}
文件: ${fileName}

\`\`\`${language}
${code.slice(0, 8000)}
\`\`\`

请给出结构化的审查报告，用中文回答。`;

        try {
            const reply = await callAI(client, prompt, token);
            showResult('🔍 7Tan 代码审查', reply);
        } catch (err: any) {
            vscode.window.showErrorMessage(`审查失败: ${err.message}`);
        }
    });
}

export async function codeReviewFolder() {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        vscode.window.showWarningMessage('请先打开一个项目文件夹');
        return;
    }

    const folder = folders[0];
    // 收集目录下主要代码文件
    const files = await vscode.workspace.findFiles(
        '**/*.{py,java,kt,swift,js,ts,jsx,tsx,go,rs,c,cpp,h}',
        '**/node_modules/**,**/.git/**,**/build/**,**/dist/**',
        50
    );

    let summary = `项目路径: ${folder.uri.fsPath}\n`;
    summary += `代码文件数(采样): ${files.length}\n\n`;

    for (const f of files.slice(0, 20)) {
        const doc = await vscode.workspace.openTextDocument(f);
        summary += `### ${f.fsPath.replace(folder.uri.fsPath, '')} (${doc.lineCount}行)\n`;
        summary += `\`\`\`\n${doc.getText().slice(0, 1000)}\n\`\`\`\n\n`;
    }

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `7Tan: 正在审查项目...`,
        cancellable: true
    }, async (progress, token) => {
        const client = getClient();
        const prompt = `请对以下项目进行代码审查概览：
1. 项目整体结构评估
2. 发现的主要问题
3. 改进建议（优先级排序）

${summary.slice(0, 12000)}`;

        try {
            const reply = await callAI(client, prompt, token);
            showResult('🔍 7Tan 项目审查', reply);
        } catch (err: any) {
            vscode.window.showErrorMessage(`审查失败: ${err.message}`);
        }
    });
}

// ── 安全扫描 ──────────────────────────────────────

export async function securityScan() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('请先打开一个文件');
        return;
    }

    const code = editor.document.getText();
    const language = editor.document.languageId;
    const fileName = editor.document.uri.fsPath.split(/[\\/]/).pop() || '';

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `7Tan: 正在安全扫描 ${fileName}...`,
        cancellable: true
    }, async (progress, token) => {
        const client = getClient();
        const prompt = `对以下代码进行安全审计，重点关注：
- SQL注入 / NoSQL注入
- XSS / CSRF
- 硬编码密钥/密码/Token
- 路径遍历
- 命令注入
- 不安全的反序列化
- 敏感信息泄露（日志、注释）
- 权限校验缺失
- 不安全的加密算法（MD5/SHA1用于密码等）

语言: ${language}
文件: ${fileName}

\`\`\`${language}
${code.slice(0, 8000)}
\`\`\`

请按严重程度（🔴严重 / 🟡中等 / 🟢低风险）列出所有安全问题。`;

        try {
            const reply = await callAI(client, prompt, token);
            showResult('🔒 7Tan 安全扫描', reply);
        } catch (err: any) {
            vscode.window.showErrorMessage(`扫描失败: ${err.message}`);
        }
    });
}

// ── AI 处理选中代码 ─────────────────────────────────

export async function explainCode() {
    await processSelection('解释代码', '请详细解释以下代码的功能、逻辑流程和关键实现细节：');
}

export async function fixCode() {
    await processSelection('修复代码', '请找出以下代码中的问题并给出修复后的完整代码。如果代码没有明显问题，请给出改进建议：');
}

export async function optimizeCode() {
    await processSelection('优化代码', '请优化以下代码，提高性能、可读性和可维护性，给出优化后的完整代码并说明改进点：');
}

export async function addComment() {
    await processSelection('添加注释', '请为以下代码添加详细的中文注释，包括函数/方法用途、参数说明、关键逻辑解释：');
}

async function processSelection(label: string, systemPrompt: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const selection = editor.selection;
    if (selection.isEmpty) {
        vscode.window.showWarningMessage('请先选中代码');
        return;
    }

    const code = editor.document.getText(selection);
    const language = editor.document.languageId;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `7Tan: ${label}...`,
        cancellable: true
    }, async (progress, token) => {
        const client = getClient();
        const prompt = `${systemPrompt}

语言: ${language}

\`\`\`${language}
${code.slice(0, 6000)}
\`\`\``;

        try {
            const reply = await callAI(client, prompt, token);
            showResult(`✨ 7Tan ${label}`, reply);
        } catch (err: any) {
            vscode.window.showErrorMessage(`${label}失败: ${err.message}`);
        }
    });
}

// ── Git 操作 ───────────────────────────────────────

export async function generateCommitMsg() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showWarningMessage('请先打开 Git 项目');
        return;
    }

    const repoPath = workspaceFolders[0].uri.fsPath;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: '7Tan: 分析 Git 变更...',
        cancellable: true
    }, async (progress, token) => {
        try {
            // 获取 git diff
            const diff = await execCommand('git diff --staged', repoPath);
            const unstaged = await execCommand('git diff', repoPath);

            if (!diff && !unstaged) {
                vscode.window.showInformationMessage('没有检测到变更');
                return;
            }

            const allDiffs = (diff + '\n' + unstaged).slice(0, 8000);

            const client = getClient();
            const prompt = `根据以下 git diff 生成一条符合 Conventional Commits 规范的提交信息：

格式: <type>(<scope>): <description>

类型: feat/fix/chore/refactor/docs/style/test/perf/ci

要求:
1. 描述用中文
2. 简洁明了（不超过72字符）
3. 如果有多个变更，用列表列出主要变更

Git Diff:
\`\`\`
${allDiffs}
\`\`\`

只输出提交信息，不要解释：`;

            const reply = await callAI(client, prompt, token);

            // 显示并让用户确认
            const choice = await vscode.window.showInformationMessage(
                `建议的 Commit 信息:\n\n${reply}`,
                { modal: true },
                '复制到剪贴板',
                '取消'
            );

            if (choice === '复制到剪贴板') {
                await vscode.env.clipboard.writeText(reply);
                vscode.window.showInformationMessage('✅ 已复制到剪贴板');
            }
        } catch (err: any) {
            vscode.window.showErrorMessage(`生成失败: ${err.message}`);
        }
    });
}

export async function gitCommit() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;

    const repoPath = workspaceFolders[0].uri.fsPath;

    // 先获取 diff，生成 AI commit message
    const diff = await execCommand('git diff --staged', repoPath);
    if (!diff) {
        vscode.window.showWarningMessage('请先 git add 暂存变更');
        return;
    }

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: '7Tan: 生成 Commit 信息...'
    }, async () => {
        const client = getClient();
        const prompt = `根据以下 git diff 生成 Conventional Commits 格式的提交信息（只输出信息）：\n\n\`\`\`\n${diff.slice(0, 4000)}\n\`\`\``;

        const msg = await callAI(client, prompt);
        const result = await execCommand(`git commit -m "${msg.replace(/"/g, '\\"')}"`, repoPath);

        if (result.includes('changed') || result.includes('insertion')) {
            vscode.window.showInformationMessage(`✅ 已提交: ${msg.split('\n')[0]}`);
        } else {
            vscode.window.showErrorMessage(`提交失败: ${result}`);
        }
    });
}

export async function gitPush() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;

    const repoPath = workspaceFolders[0].uri.fsPath;
    const result = await execCommand('git push', repoPath);
    vscode.window.showInformationMessage(result.slice(0, 200));
}

export async function gitLog() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;

    const repoPath = workspaceFolders[0].uri.fsPath;
    const log = await execCommand('git log --oneline --graph --all -30', repoPath);
    showResult('📜 Git 提交历史', log);
}

// ── ADB ────────────────────────────────────────────

export async function adbInstall() {
    const files = await vscode.window.showOpenDialog({
        filters: { 'APK 文件': ['apk'] },
        title: '选择要安装的 APK'
    });

    if (!files || files.length === 0) return;

    const apkPath = files[0].fsPath;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `7Tan: 正在安装 ${apkPath.split(/[\\/]/).pop()}...`
    }, async () => {
        const result = await execCommand(`adb install -r "${apkPath}"`);
        if (result.includes('Success')) {
            vscode.window.showInformationMessage('✅ APK 安装成功');
        } else {
            vscode.window.showErrorMessage(`安装失败: ${result}`);
        }
    });
}

// ── 配置 ───────────────────────────────────────────

export async function configure() {
    const apiKey = await vscode.window.showInputBox({
        prompt: '输入 DeepSeek API Key（留空使用 7Tan 本地代理）',
        password: true,
        placeHolder: 'sk-...',
        value: vscode.workspace.getConfiguration("7tan.api").get<string>("key", "")
    });

    if (apiKey !== undefined) {
        const cfg = vscode.workspace.getConfiguration("7tan.api");
        await cfg.update("key", apiKey, vscode.ConfigurationTarget.Global);

        const endpoint = await vscode.window.showInputBox({
            prompt: '7Tan 后端地址',
            placeHolder: 'http://127.0.0.1:17890',
            value: vscode.workspace.getConfiguration("7tan.api").get<string>("endpoint", "http://127.0.0.1:17890")
        });

        if (endpoint) {
            await cfg.update("endpoint", endpoint, vscode.ConfigurationTarget.Global);
        }

        vscode.window.showInformationMessage('✅ 7Tan 配置已保存');
    }
}

// ── 打开聊天面板 ────────────────────────────────────

export async function openChat(message?: string) {
    await vscode.commands.executeCommand('7tan.chatView.focus');
    if (message) {
        // 如果提供了消息，模拟发送
        // 这需要通过 chatPanel 实例来操作
    }
}

// ── 辅助函数 ───────────────────────────────────────

async function callAI(
    client: TanClient,
    prompt: string,
    cancelToken?: vscode.CancellationToken
): Promise<string> {
    // 优先通过 7Tan 后端
    try {
        const isOnline = await client.ping();
        if (isOnline) {
            const resp = await client.chat({ message: prompt }, cancelToken);
            if (resp.success && resp.reply) return resp.reply;
        }
    } catch {
        // 后端离线，直连 DeepSeek
    }

    return client.directDeepSeek([
        { role: "system", content: "你是 7Tan AI 编程助手。用中文回答，代码块加语言标记。" },
        { role: "user", content: prompt }
    ], 2048, cancelToken);
}

function execCommand(cmd: string, cwd?: string): Promise<string> {
    return new Promise((resolve, reject) => {
        child_process.exec(cmd, { cwd, maxBuffer: 1024 * 1024 }, (err, stdout, stderr) => {
            if (err && !stdout) reject(err);
            else resolve(stdout || stderr);
        });
    });
}

function showResult(title: string, content: string) {
    // 创建输出面板
    const outputChannel = vscode.window.createOutputChannel('7Tan', 'markdown');
    outputChannel.clear();
    outputChannel.appendLine(`# ${title}\n`);
    outputChannel.append(content);
    outputChannel.show(true);
}
