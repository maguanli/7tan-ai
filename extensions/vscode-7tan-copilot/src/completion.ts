/**
 * 7Tan 代码补全 Provider — 行内补全 (InlineCompletion)
 */

import * as vscode from 'vscode';
import { getClient } from './client';

export class TanCompletionProvider implements vscode.InlineCompletionItemProvider {

    name = "7Tan Copilot";

    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {

        const config = vscode.workspace.getConfiguration("7tan.completion");
        if (!config.get<boolean>("enabled", true)) return [];
        if (token.isCancellationRequested) return [];

        const client = getClient();

        // 优先通过 7Tan 后端补全
        try {
            const isOnline = await client.ping();
            if (isOnline) {
                return this.completeVia7tan(document, position, client, token);
            }
        } catch {
            // 后端离线，尝试直连 DeepSeek
        }

        return this.completeViaDeepSeek(document, position, client, token);
    }

    /** 通过 7Tan 后端补全 */
    private async completeVia7tan(
        document: vscode.TextDocument,
        position: vscode.Position,
        client: ReturnType<typeof getClient>,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        const prefix = this.getPrefix(document, position);
        const suffix = this.getSuffix(document, position);

        const resp = await client.complete({
            prefix,
            suffix,
            language: document.languageId,
            file_path: document.uri.fsPath
        }, token);

        if (!resp?.success || !resp.completion) return [];
        return [this.makeItem(resp.completion, position)];
    }

    /** 直连 DeepSeek 补全 */
    private async completeViaDeepSeek(
        document: vscode.TextDocument,
        position: vscode.Position,
        client: ReturnType<typeof getClient>,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        const apiKey = vscode.workspace.getConfiguration("7tan.api").get<string>("key", "");
        if (!apiKey) return [];

        const prefix = this.getPrefix(document, position);
        const suffix = this.getSuffix(document, position);
        const maxTokens = vscode.workspace.getConfiguration("7tan.completion").get<number>("maxTokens", 128);

        const prompt = `你是代码补全助手，根据上下文直接补全代码。

语言: ${document.languageId}
文件: ${document.uri.fsPath}

上文 (光标前):
\`\`\`${document.languageId}
${prefix.slice(-2000)}
\`\`\`

下文 (光标后):
\`\`\`${document.languageId}
${suffix.slice(0, 500)}
\`\`\`

请直接在光标位置补全代码（只补全缺失部分，不要重复已有代码），控制在1-10行内。
只输出纯代码，不要加解释、不要加markdown标记:`;

        try {
            const completion = await client.directDeepSeek([
                { role: "system", content: "你是代码补全专家。只输出需要补全的代码，不要任何解释。" },
                { role: "user", content: prompt }
            ], maxTokens, token);

            if (!completion || completion.length > 2000) return [];
            return [this.makeItem(completion, position)];

        } catch {
            return [];
        }
    }

    private makeItem(text: string, position: vscode.Position): vscode.InlineCompletionItem {
        return new vscode.InlineCompletionItem(text, new vscode.Range(position, position));
    }

    private getPrefix(document: vscode.TextDocument, position: vscode.Position): string {
        const startLine = Math.max(0, position.line - 100);
        const range = new vscode.Range(startLine, 0, position.line, position.character);
        return document.getText(range);
    }

    private getSuffix(document: vscode.TextDocument, position: vscode.Position): string {
        const endLine = Math.min(document.lineCount - 1, position.line + 50);
        const range = new vscode.Range(
            position.line, position.character,
            endLine, document.lineAt(endLine).text.length
        );
        return document.getText(range);
    }
}
