/**
 * 7Tan Copilot — VS Code 扩展
 * 
 * 实时代码补全：在用户输入时，获取上下文，调用 7Tan/DeepSeek API，
 * 返回 AI 生成的代码补全建议（Ghost Text / 行内补全）。
 */

import * as vscode from 'vscode';
import * as http from 'http';
import * as https from 'https';

// ── 配置 ─────────────────────────────────────────
let isEnabled = true;

// ── 补全 Provider ────────────────────────────────
class TanCompletionProvider implements vscode.InlineCompletionItemProvider {
    
    name = "7Tan Copilot";

    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        
        if (!isEnabled) return [];
        if (token.isCancellationRequested) return [];

        const config = vscode.workspace.getConfiguration("7tan-copilot");
        const apiKey = config.get<string>("deepseekApiKey", "");
        const maxTokens = config.get<number>("maxTokens", 128);
        
        if (!apiKey) {
            // 没有 API Key，尝试通过 7Tan 代理
            return this.completeVia7tan(document, position, token);
        }

        // 直接调用 DeepSeek API
        return this.completeViaDeepSeek(document, position, apiKey, maxTokens, token);
    }

    /**
     * 通过 7Tan 本地代理获取补全（需要 7Tan 应用在运行）
     */
    private async completeVia7tan(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        const config = vscode.workspace.getConfiguration("7tan-copilot");
        const endpoint = config.get<string>("apiEndpoint", "http://127.0.0.1:17890/api/complete");

        const prefix = this.getPrefix(document, position);
        const suffix = this.getSuffix(document, position);
        const language = document.languageId;

        try {
            const response = await httpPost(endpoint, {
                prefix,
                suffix,
                language,
                file_path: document.uri.fsPath
            }, token);

            if (!response || !response.success) return [];

            // 如果 7Tan 返回了补全文本
            if (response.completion) {
                return [new vscode.InlineCompletionItem(
                    response.completion,
                    new vscode.Range(position, position)
                )];
            }

            // 如果 7Tan 只返回了 prompt（需要 AI 处理）
            if (response.prompt) {
                // 尝试直接调 DeepSeek
                return [];
            }

            return [];
        } catch {
            return [];
        }
    }

    /**
     * 直接调用 DeepSeek API
     */
    private async completeViaDeepSeek(
        document: vscode.TextDocument,
        position: vscode.Position,
        apiKey: string,
        maxTokens: number,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        
        const prefix = this.getPrefix(document, position);
        const suffix = this.getSuffix(document, position);
        const language = document.languageId;

        const prompt = `你是代码补全助手，根据上下文直接补全代码。

语言: ${language}
文件: ${document.uri.fsPath}

上文 (光标前):
\`\`\`${language}
${prefix.slice(-2000)}
\`\`\`

下文 (光标后):
\`\`\`${language}
${suffix.slice(0, 500)}
\`\`\`

请直接在光标位置补全代码（只补全缺失部分，不要重复已有代码），控制在1-10行内。
只输出纯代码，不要加解释、不要加markdown标记:`;

        try {
            const body = JSON.stringify({
                model: "deepseek-chat",
                messages: [
                    { role: "system", content: "你是代码补全专家。只输出需要补全的代码，不要任何解释。" },
                    { role: "user", content: prompt }
                ],
                max_tokens: maxTokens,
                temperature: 0.1,
                stop: ["\n\n\n"]
            });

            const result = await httpsRequest({
                hostname: "api.deepseek.com",
                path: "/v1/chat/completions",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${apiKey}`
                }
            }, body, token);

            const data = JSON.parse(result);
            const completion = data.choices?.[0]?.message?.content?.trim();

            if (!completion || completion.length === 0 || completion.length > 2000) {
                return [];
            }

            return [new vscode.InlineCompletionItem(
                completion,
                new vscode.Range(position, position)
            )];

        } catch {
            return [];
        }
    }

    private getPrefix(document: vscode.TextDocument, position: vscode.Position): string {
        const startLine = Math.max(0, position.line - 100);
        const range = new vscode.Range(startLine, 0, position.line, position.character);
        return document.getText(range);
    }

    private getSuffix(document: vscode.TextDocument, position: vscode.Position): string {
        const endLine = Math.min(document.lineCount - 1, position.line + 50);
        const range = new vscode.Range(position.line, position.character, endLine, 
            document.lineAt(endLine).text.length);
        return document.getText(range);
    }
}

// ── HTTP 工具函数 ─────────────────────────────────

function httpPost(url: string, data: any, cancelToken: vscode.CancellationToken): Promise<any> {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify(data);
        const u = new URL(url);
        const opts: http.RequestOptions = {
            hostname: u.hostname,
            port: u.port || 80,
            path: u.pathname,
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(body).toString()
            },
            timeout: 5000
        };

        const req = http.request(opts, (res) => {
            let out = "";
            res.on("data", (chunk) => out += chunk);
            res.on("end", () => {
                try { resolve(JSON.parse(out)); }
                catch { resolve(null); }
            });
        });

        req.on("error", reject);
        req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });

        cancelToken.onCancellationRequested(() => { req.destroy(); });

        req.write(body);
        req.end();
    });
}

function httpsRequest(opts: https.RequestOptions, body: string, cancelToken: vscode.CancellationToken): Promise<string> {
    return new Promise((resolve, reject) => {
        const req = https.request(opts, (res) => {
            let out = "";
            res.on("data", (chunk) => out += chunk);
            res.on("end", () => resolve(out));
        });
        req.on("error", reject);
        req.setTimeout(10000, () => { req.destroy(); reject(new Error("timeout")); });
        cancelToken.onCancellationRequested(() => { req.destroy(); });
        req.write(body);
        req.end();
    });
}

// ── 扩展激活 ──────────────────────────────────────

let provider: TanCompletionProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log("7Tan Copilot 已激活");

    provider = new TanCompletionProvider();

    // 注册行内补全 Provider（所有语言）
    const completionRegistration = vscode.languages.registerInlineCompletionItemProvider(
        { pattern: "**" },
        provider
    );

    // 切换开关
    const toggleCmd = vscode.commands.registerCommand("7tan-copilot.toggle", () => {
        isEnabled = !isEnabled;
        vscode.window.showInformationMessage(
            `7Tan Copilot: ${isEnabled ? "✅ 已启用" : "⏸️ 已禁用"}`
        );
    });

    // 配置命令
    const configCmd = vscode.commands.registerCommand("7tan-copilot.configure", async () => {
        const apiKey = await vscode.window.showInputBox({
            prompt: "输入 DeepSeek API Key（留空使用 7Tan 代理）",
            password: true,
            placeHolder: "sk-..."
        });
        if (apiKey !== undefined) {
            const cfg = vscode.workspace.getConfiguration("7tan-copilot");
            await cfg.update("deepseekApiKey", apiKey, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage("✅ 7Tan Copilot 配置已保存");
        }
    });

    // 状态栏
    const statusBar = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right, 100
    );
    statusBar.text = "$(sparkle) 7Tan";
    statusBar.tooltip = "7Tan Copilot — 点击切换";
    statusBar.command = "7tan-copilot.toggle";
    statusBar.show();

    context.subscriptions.push(
        completionRegistration,
        toggleCmd,
        configCmd,
        statusBar
    );
}

export function deactivate() {
    console.log("7Tan Copilot 已停用");
}
