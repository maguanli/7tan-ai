/**
 * 7Tan AI 侧边栏 Provider
 * 提供 VS Code 侧边栏中的 AI 对话 Webview
 */

const vscode = require('vscode');

class SidebarProvider {
    /**
     * @param {vscode.Uri} extensionUri
     * @param {import('./apiClient').ApiClient} apiClient
     */
    constructor(extensionUri, apiClient) {
        this._extensionUri = extensionUri;
        this._apiClient = apiClient;
        this._view = null;
        this._sessionId = null;
    }

    /**
     * 外部发送消息到侧边栏
     * @param {string} message
     */
    sendMessage(message) {
        if (this._view) {
            this._view.webview.postMessage({
                type: 'sendMessage',
                message: message
            });
        }
    }

    /**
     * VS Code 调用：创建 Webview
     * @param {vscode.WebviewView} webviewView
     * @param {vscode.WebviewViewResolveContext} context
     * @param {vscode.CancellationToken} token
     */
    resolveWebviewView(webviewView, context, token) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlContent(webviewView.webview);

        // 处理来自 Webview 的消息
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'chat':
                    await this._handleChat(data.message);
                    break;
                case 'newSession':
                    this._sessionId = null;
                    webviewView.webview.postMessage({
                        type: 'sessionReset',
                        message: '新会话已创建'
                    });
                    break;
                case 'getHistory':
                    await this._handleGetHistory();
                    break;
                case 'insertCode':
                    await vscode.commands.executeCommand('7tan.insertToEditor', data.code);
                    break;
                case 'showInfo':
                    vscode.window.showInformationMessage(data.message);
                    break;
            }
        });
    }

    /**
     * 处理 AI 对话
     * @param {string} message
     */
    async _handleChat(message) {
        if (!this._view) return;

        // 显示"思考中"
        this._view.webview.postMessage({
            type: 'thinking',
            message: '🤔 7Tan 正在思考...'
        });

        try {
            const response = await this._apiClient.sendMessage(
                message,
                this._sessionId,
                null  // 使用默认模型
            );

            if (response && response.session_id) {
                this._sessionId = response.session_id;
            }

            if (response && response.success) {
                this._view.webview.postMessage({
                    type: 'response',
                    message: response.result,
                    cost: response.cost || 0,
                    sessionId: response.session_id
                });
            } else {
                this._view.webview.postMessage({
                    type: 'error',
                    message: response?.result || '未知错误，请检查 7Tan 服务是否运行'
                });
            }
        } catch (err) {
            this._view.webview.postMessage({
                type: 'error',
                message: `❌ 连接失败：${err.message}\n\n请确保 7Tan 已启动（localhost:9800）`
            });
        }
    }

    /**
     * 获取对话历史
     */
    async _handleGetHistory() {
        if (!this._view || !this._sessionId) return;

        try {
            const history = await this._apiClient.getHistory(this._sessionId);
            if (history && history.messages) {
                this._view.webview.postMessage({
                    type: 'history',
                    messages: history.messages
                });
            }
        } catch {
            // 静默失败
        }
    }

    /**
     * 生成 Webview HTML
     * @param {vscode.Webview} webview
     * @returns {string}
     */
    _getHtmlContent(webview) {
        // 使用内联样式，不依赖外部 CSS 文件
        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" 
          content="default-src 'none'; 
                   style-src 'unsafe-inline' ${webview.cspSource}; 
                   script-src 'unsafe-inline' ${webview.cspSource};
                   img-src data:;">
    <title>7Tan AI</title>
    <style>
        :root {
            --bg: var(--vscode-sideBar-background);
            --fg: var(--vscode-sideBar-foreground);
            --input-bg: var(--vscode-input-background);
            --input-fg: var(--vscode-input-foreground);
            --border: var(--vscode-input-border);
            --btn-bg: var(--vscode-button-background);
            --btn-fg: var(--vscode-button-foreground);
            --btn-hover: var(--vscode-button-hoverBackground);
            --accent: #6C5CE7;
            --user-bubble: var(--vscode-textBlockQuote-background);
            --ai-bubble: transparent;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--fg);
            background: var(--bg);
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }

        /* ---- 头部 ---- */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }
        .header .logo {
            font-weight: 700;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .header .logo .icon { font-size: 18px; }
        .header .actions {
            display: flex;
            gap: 6px;
        }
        .header button {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--fg);
            padding: 3px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }
        .header button:hover { background: var(--btn-hover); }

        /* ---- 消息区 ---- */
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .messages::-webkit-scrollbar {
            width: 6px;
        }
        .messages::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 3px;
        }

        .message {
            padding: 10px 12px;
            border-radius: 8px;
            line-height: 1.5;
            word-wrap: break-word;
            white-space: pre-wrap;
            animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            background: var(--user-bubble);
            align-self: flex-end;
            max-width: 90%;
        }

        .message.ai {
            background: var(--ai-bubble);
            align-self: flex-start;
            max-width: 100%;
            border-left: 3px solid var(--accent);
            padding-left: 10px;
        }

        .message.thinking {
            align-self: flex-start;
            opacity: 0.7;
            font-style: italic;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }

        .message.error {
            background: rgba(255, 99, 71, 0.1);
            border-left: 3px solid tomato;
            align-self: flex-start;
            max-width: 100%;
        }

        /* 代码块样式 */
        .message pre {
            background: var(--vscode-textCodeBlock-background);
            color: var(--vscode-textCodeBlock-foreground);
            padding: 10px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 8px 0;
            position: relative;
        }
        .message code {
            font-family: var(--vscode-editor-font-family);
            font-size: 12px;
        }
        .copy-btn {
            position: absolute;
            top: 4px;
            right: 4px;
            background: var(--btn-bg);
            color: var(--btn-fg);
            border: none;
            padding: 2px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 10px;
            opacity: 0;
            transition: opacity 0.2s;
        }
        .message pre:hover .copy-btn { opacity: 1; }

        .meta {
            font-size: 10px;
            opacity: 0.5;
            margin-top: 4px;
        }

        /* ---- 输入区 ---- */
        .input-area {
            display: flex;
            gap: 6px;
            padding: 10px 12px;
            border-top: 1px solid var(--border);
            flex-shrink: 0;
        }
        .input-area textarea {
            flex: 1;
            background: var(--input-bg);
            color: var(--input-fg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 10px;
            font-family: inherit;
            font-size: 13px;
            resize: none;
            min-height: 36px;
            max-height: 120px;
            outline: none;
        }
        .input-area textarea:focus {
            border-color: var(--accent);
        }
        .input-area button {
            background: var(--btn-bg);
            color: var(--btn-fg);
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            align-self: flex-end;
        }
        .input-area button:hover { opacity: 0.9; }
        .input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
    </style>
</head>
<body>
    <!-- 头部 -->
    <div class="header">
        <div class="logo">
            <span class="icon">🎮</span> 7Tan AI
        </div>
        <div class="actions">
            <button onclick="newSession()" title="新建会话">＋</button>
        </div>
    </div>

    <!-- 消息区 -->
    <div class="messages" id="messages">
        <div class="message ai">
            👋 你好！我是 <b>7Tan AI 助手</b><br><br>
            我可以帮你：<br>
            🔍 <b>审查代码</b> — 右键选中代码 → 审查代码<br>
            📖 <b>解释代码</b> — 右键选中代码 → 解释代码<br>
            🚀 <b>优化代码</b> — 右键选中代码 → 优化代码<br>
            🧪 <b>生成测试</b> — 右键选中代码 → 生成测试<br>
            ✨ <b>生成代码</b> — Ctrl+Shift+P → 7Tan: 生成代码<br><br>
            也可以直接在下方输入框问我任何问题！
        </div>
    </div>

    <!-- 输入区 -->
    <div class="input-area">
        <textarea id="input" 
                  placeholder="输入消息，按 Enter 发送，Shift+Enter 换行..."
                  rows="1"
                  onkeydown="handleKeydown(event)"></textarea>
        <button id="sendBtn" onclick="sendMessage()">发送</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('input');
        const sendBtn = document.getElementById('sendBtn');
        let isWaiting = false;

        // ---- 发送消息 ----
        function sendMessage() {
            const msg = inputEl.value.trim();
            if (!msg || isWaiting) return;

            // 显示用户消息
            appendMessage('user', msg);
            inputEl.value = '';
            inputEl.style.height = 'auto';
            isWaiting = true;
            sendBtn.disabled = true;

            // 发送给扩展
            vscode.postMessage({ type: 'chat', message: msg });
        }

        function handleKeydown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        // ---- 自动调整输入框高度 ----
        inputEl.addEventListener('input', () => {
            inputEl.style.height = 'auto';
            inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
        });

        // ---- 新建会话 ----
        function newSession() {
            messagesEl.innerHTML = '';
            appendMessage('ai', '🆕 新会话已创建，开始对话吧！');
            vscode.postMessage({ type: 'newSession' });
        }

        // ---- 添加消息 ----
        function appendMessage(role, content, cost) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.innerHTML = formatContent(content);
            if (cost) {
                div.innerHTML += '<div class="meta">💰 费用: ¥' + cost.toFixed(4) + '</div>';
            }
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;

            // 给代码块加复制按钮
            div.querySelectorAll('pre').forEach(pre => {
                if (!pre.querySelector('.copy-btn')) {
                    const btn = document.createElement('button');
                    btn.className = 'copy-btn';
                    btn.textContent = '📋 复制';
                    btn.onclick = () => copyCode(pre, btn);
                    pre.style.position = 'relative';
                    pre.appendChild(btn);
                }
            });
        }

        // ---- 格式化内容（Markdown 简单渲染） ----
        function formatContent(text) {
            if (!text) return '';

            // 转义 HTML
            let html = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // 代码块 ```...```
            html = html.replace(/\`\`\`(\w*)\\n?([\\s\\S]*?)\`\`\`/g, (_, lang, code) => {
                return '<pre><code class="language-' + lang + '">' + code.trim() + '</code></pre>';
            });

            // 行内代码 `...`
            html = html.replace(/\`([^\`]+)\`/g, '<code>$1</code>');

            // 加粗 **...**
            html = html.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');

            // 换行
            html = html.replace(/\\n/g, '<br>');

            return html;
        }

        // ---- 复制代码 ----
        function copyCode(pre, btn) {
            const code = pre.querySelector('code')?.textContent || pre.textContent;
            navigator.clipboard.writeText(code).then(() => {
                btn.textContent = '✅ 已复制';
                setTimeout(() => { btn.textContent = '📋 复制'; }, 2000);
            }).catch(() => {
                // Fallback: 通过 VS Code 插入
                vscode.postMessage({ type: 'insertCode', code: code });
                btn.textContent = '✅ 已插入';
                setTimeout(() => { btn.textContent = '📋 复制'; }, 2000);
            });
        }

        // ---- 接收来自扩展的消息 ----
        window.addEventListener('message', event => {
            const data = event.data;

            // 移除"思考中"
            const thinkingEl = messagesEl.querySelector('.thinking');
            if (thinkingEl) thinkingEl.remove();

            switch (data.type) {
                case 'sendMessage':
                    // 外部触发的消息（如右键菜单）
                    appendMessage('user', data.message);
                    vscode.postMessage({ type: 'chat', message: data.message });
                    isWaiting = true;
                    sendBtn.disabled = true;
                    break;

                case 'thinking':
                    appendMessage('thinking', data.message);
                    break;

                case 'response':
                    appendMessage('ai', data.message, data.cost);
                    isWaiting = false;
                    sendBtn.disabled = false;
                    inputEl.focus();
                    break;

                case 'error':
                    appendMessage('error', data.message);
                    isWaiting = false;
                    sendBtn.disabled = false;
                    break;

                case 'sessionReset':
                    appendMessage('ai', data.message);
                    break;
            }
        });
    </script>
</body>
</html>`;
    }
}

module.exports = { SidebarProvider };
