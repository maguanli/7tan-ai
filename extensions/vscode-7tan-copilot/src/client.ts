/**
 * 7Tan HTTP 客户端 — 与 7Tan 桌面应用后端通信
 */

import * as http from 'http';
import * as https from 'https';
import * as vscode from 'vscode';

export interface ChatRequest {
    message: string;
    context?: string;
    language?: string;
}

export interface ChatResponse {
    success: boolean;
    reply: string;
    error?: string;
}

export interface CompletionRequest {
    prefix: string;
    suffix: string;
    language: string;
    file_path: string;
    max_tokens?: number;
}

export interface CompletionResponse {
    success: boolean;
    completion?: string;
    prompt?: string;
    error?: string;
}

export class TanClient {
    private baseUrl: string;

    constructor() {
        const config = vscode.workspace.getConfiguration("7tan.api");
        this.baseUrl = config.get<string>("endpoint", "http://127.0.0.1:17890");
    }

    /** 向 7Tan 后端发送聊天消息 */
    async chat(request: ChatRequest, cancelToken?: vscode.CancellationToken): Promise<ChatResponse> {
        return this.post<ChatResponse>('/api/chat', request, cancelToken);
    }

    /** 请求代码补全 */
    async complete(request: CompletionRequest, cancelToken?: vscode.CancellationToken): Promise<CompletionResponse> {
        return this.post<CompletionResponse>('/api/complete', request, cancelToken);
    }

    /** 代码审查 */
    async reviewCode(code: string, language: string, cancelToken?: vscode.CancellationToken): Promise<ChatResponse> {
        return this.post<ChatResponse>('/api/review', { code, language }, cancelToken);
    }

    /** 安全扫描 */
    async securityScan(code: string, language: string, cancelToken?: vscode.CancellationToken): Promise<ChatResponse> {
        return this.post<ChatResponse>('/api/security', { code, language }, cancelToken);
    }

    /** 生成 commit 信息 */
    async generateCommit(diff: string, cancelToken?: vscode.CancellationToken): Promise<ChatResponse> {
        return this.post<ChatResponse>('/api/commit-msg', { diff }, cancelToken);
    }

    /** 检查后端是否在线 */
    async ping(): Promise<boolean> {
        try {
            const resp = await this.post<{ success: boolean }>('/api/ping', {});
            return resp?.success === true;
        } catch {
            return false;
        }
    }

    /** 直接调用 DeepSeek API（无需 7Tan 后端） */
    async directDeepSeek(
        messages: Array<{ role: string; content: string }>,
        maxTokens: number = 1024,
        cancelToken?: vscode.CancellationToken
    ): Promise<string> {
        const apiKey = vscode.workspace.getConfiguration("7tan.api").get<string>("key", "");
        if (!apiKey) {
            throw new Error("请先配置 DeepSeek API Key（Ctrl+Shift+P → 7Tan: 配置 API）");
        }

        const body = JSON.stringify({
            model: "deepseek-chat",
            messages,
            max_tokens: maxTokens,
            temperature: 0.3
        });

        return new Promise((resolve, reject) => {
            const opts: https.RequestOptions = {
                hostname: "api.deepseek.com",
                path: "/v1/chat/completions",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${apiKey}`,
                    "Content-Length": Buffer.byteLength(body).toString()
                },
                timeout: 30000
            };

            const req = https.request(opts, (res) => {
                let out = "";
                res.on("data", (chunk: Buffer) => out += chunk.toString());
                res.on("end", () => {
                    try {
                        const data = JSON.parse(out);
                        const reply = data.choices?.[0]?.message?.content?.trim();
                        resolve(reply || "(无响应)");
                    } catch {
                        reject(new Error(`解析失败: ${out.slice(0, 200)}`));
                    }
                });
            });

            req.on("error", reject);
            req.setTimeout(30000, () => { req.destroy(); reject(new Error("超时")); });
            cancelToken?.onCancellationRequested(() => req.destroy());
            req.write(body);
            req.end();
        });
    }

    /** 通用 POST 请求 */
    private post<T>(path: string, data: any, cancelToken?: vscode.CancellationToken): Promise<T> {
        return new Promise((resolve, reject) => {
            const body = JSON.stringify(data);
            const u = new URL(this.baseUrl + path);

            const opts: http.RequestOptions = {
                hostname: u.hostname,
                port: u.port || 80,
                path: u.pathname + u.search,
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(body).toString()
                },
                timeout: 15000
            };

            const req = http.request(opts, (res) => {
                let out = "";
                res.on("data", (chunk: Buffer) => out += chunk.toString());
                res.on("end", () => {
                    try { resolve(JSON.parse(out)); }
                    catch { resolve({ success: false, reply: out } as any); }
                });
            });

            req.on("error", reject);
            req.setTimeout(15000, () => { req.destroy(); reject(new Error("7Tan 后端连接超时")); });
            cancelToken?.onCancellationRequested(() => req.destroy());
            req.write(body);
            req.end();
        });
    }
}

// 单例
let _instance: TanClient;
export function getClient(): TanClient {
    if (!_instance) _instance = new TanClient();
    return _instance;
}
