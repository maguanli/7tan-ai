/**
 * 7Tan AI 对话面板 — 侧边栏 WebView
 */

import * as vscode from 'vscode';
import { getClient } from './client';

export class TanChatPanel implements vscode.WebviewViewProvider {

    public static readonly viewType = '7tan.chatView';
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this.getHtml();

        // 处理来自 WebView 的消息
        webviewView.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.type) {
                case 'sendMessage':
                    await this.handleChat(msg.text);
                    break;
                case 'ping':
                    this.postMessage({ type: 'pong' });
                    break;
            }
        });
    }

    /** 发送消息到 WebView */
    private postMessage(data: any) {
        this._view?.webview.postMessage(data);
    }

    /** 处理用户消息 */
    private async handleChat(userMessage: string) {
        this.postMessage({ type: 'thinking', text: '思考中...' });

        try {
            const client = getClient();
            const editor = vscode.window.activeTextEditor;
            let context = '';

            if (editor) {
                const selection = editor.selection;
                const selectedText = selection.isEmpty
                    ? editor.document.getText()
                    : editor.document.getText(selection);
                context = `当前文件: ${editor.document.uri.fsPath}\n语言: ${editor.document.languageId}\n代码:\n\`\`\`\n${selectedText.slice(0, 4000)}\n\`\`\``;
            }

            // 优先通过 7Tan 后端
            let reply = '';
            try {
                const isOnline = await client.ping();
                if (isOnline) {
                    const resp = await client.chat({ message: userMessage, context });
                    reply = resp.reply || '无响应';
                } else {
                    reply = await client.directDeepSeek([
                        { role: "system", content: "你是 7Tan AI 编程助手，帮助用户解答问题。回答用中文，代码块加语言标记。" },
                        { role: "user", content: `上下文:\n${context}\n\n问题: ${userMessage}` }
                    ]);
                }
            } catch {
                reply = await client.directDeepSeek([
                    { role: "system", content: "你是 7Tan AI 编程助手，帮助用户解答问题。回答用中文，代码块加语言标记。" },
                    { role: "user", content: userMessage }
                ]);
            }

            this.postMessage({ type: 'reply', text: reply });
        } catch (err: any) {
            this.postMessage({ type: 'error', text: `错误: ${err.message}` });
        }
    }

    /** 公开方法：在面板中显示消息 */
    showMessage(text: string) {
        this._view?.show?.(true);
        this.postMessage({ type: 'reply', text });
    }

    /** 生成聊天面板 HTML */
    private getHtml(): string {
        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { 
    font-family: var(--vscode-font-family, 'Segoe UI', sans-serif);
    font-size: 13px; 
    color: var(--vscode-foreground);
    background: var(--vscode-sideBar-background);
    display:flex; flex-direction:column; height:100vh;
}
#messages { 
    flex:1; overflow-y:auto; padding:10px;
    display:flex; flex-direction:column; gap:8px;
}
.msg { 
    padding:8px 12px; border-radius:12px; max-width:90%;
    line-height:1.5; white-space:pre-wrap; word-break:break-word;
}
.msg.user { 
    align-self:flex-end; 
    background: var(--vscode-button-background); 
    color: var(--vscode-button-foreground);
}
.msg.assistant { 
    align-self:flex-start;
    background: var(--vscode-editor-background);
    border:1px solid var(--vscode-widget-border);
}
.msg.system { 
    align-self:center; font-size:11px; opacity:0.7;
    font-style:italic;
}
.msg.error {
    align-self:flex-start;
    background: var(--vscode-inputValidation-errorBackground);
    border:1px solid var(--vscode-inputValidation-errorBorder);
}
#input-area {
    display:flex; padding:8px; gap:6px;
    border-top:1px solid var(--vscode-widget-border);
}
#input-area textarea {
    flex:1; resize:none; border:1px solid var(--vscode-widget-border);
    border-radius:8px; padding:8px; font-size:13px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    font-family: inherit; min-height:36px; max-height:120px;
}
#input-area button {
    padding:8px 14px; border:none; border-radius:8px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    cursor:pointer; font-size:13px;
}
#input-area button:hover { background: var(--vscode-button-hoverBackground); }
#input-area button:disabled { opacity:0.5; cursor:default; }
pre { 
    background: var(--vscode-textCodeBlock-background);
    border-radius:6px; padding:8px; overflow-x:auto;
    margin:4px 0;
}
code { font-family: var(--vscode-editor-font-family, monospace); font-size:12px; }
</style>
</head>
<body>
<div id="messages">
    <div class="msg system">🎮 7Tan AI 已就绪，可以开始对话</div>
</div>
<div id="input-area">
    <textarea id="input" rows="1" placeholder="输入问题，Enter 发送，Shift+Enter 换行..."
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send();}"></textarea>
    <button onclick="send()" id="sendBtn">发送</button>
</div>

<script>
const vscode = acquireVsCodeApi();
const msgsEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
let loading = false;

function addMsg(text, cls) {
    const div = document.createElement('div');
    div.className = 'msg ' + cls;
    div.innerHTML = formatText(text);
    msgsEl.appendChild(div);
    msgsEl.scrollTop = msgsEl.scrollHeight;
    return div;
}

function formatText(text) {
    return text
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/\`\`\`(\w*)\n([\s\S]*?)\`\`\`/g, '<pre><code>$2</code></pre>')
        .replace(/\`([^\`]+)\`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

function send() {
    const text = inputEl.value.trim();
    if (!text || loading) return;
    addMsg(text, 'user');
    inputEl.value = '';
    inputEl.style.height = 'auto';
    loading = true;
    sendBtn.disabled = true;
    vscode.postMessage({ type: 'sendMessage', text });
}

let thinkingEl = null;
window.addEventListener('message', e => {
    const msg = e.data;
    switch(msg.type) {
        case 'thinking':
            if (!thinkingEl) thinkingEl = addMsg(msg.text, 'system');
            else thinkingEl.textContent = msg.text;
            break;
        case 'reply':
            if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
            addMsg(msg.text, 'assistant');
            loading = false;
            sendBtn.disabled = false;
            break;
        case 'error':
            if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
            addMsg(msg.text, 'error');
            loading = false;
            sendBtn.disabled = false;
            break;
    }
});

// 自适应高度
inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});
</script>
</body>
</html>`;
    }
}
