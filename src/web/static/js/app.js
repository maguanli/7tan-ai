/**
 * Vue 3 主应用
 * 初始化、挂载、WebSocket 连接
 * 详见架构文档 §21.1
 */
const App = {
    // ===== WebSocket =====
    _ws: null,
    _reconnectTimer: null,
    _reconnectDelay: 1000,

    wsSend(data) {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
            this._ws.send(JSON.stringify(data));
        }
    },

    _connectWS() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        this._ws = new WebSocket(`${proto}://${location.host}/ws`);

        this._ws.onopen = () => {
            Store.wsConnected = true;
            Store.wsReconnectAttempts = 0;
            this._reconnectDelay = 1000;
            console.log('🔌 WebSocket 已连接');
        };

        this._ws.onclose = () => {
            Store.wsConnected = false;
            Store.wsReconnectAttempts++;
            const delay = Math.min(this._reconnectDelay * 1.5, 15000);
            this._reconnectTimer = setTimeout(() => this._connectWS(), delay);
            this._reconnectDelay = delay;
            console.log(`🔌 WebSocket 断开，${delay/1000}s 后重连 (第${Store.wsReconnectAttempts}次)`);
        };

        this._ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this._handleMessage(data);
            } catch (err) {
                console.error('WebSocket 消息解析失败:', err);
            }
        };
    },

    _handleMessage(data) {
        const type = data.type;

        switch (type) {
            case 'pong':
                break;

            case 'chat_done':
                Actions.addChatMessage({
                    role: 'assistant',
                    content: data.result || '任务完成',
                    cost: data.cost || 0,
                });
                Store.chatLoading = false;
                Store.currentSessionId = data.session_id;
                // 刷新会话列表
                Actions.fetchSessions();
                break;

            case 'chat_start':
                Store.currentSessionId = data.session_id;
                break;

            case 'chat_history':
                // 加载历史消息到当前聊天
                Store.chatMessages = (data.messages || []).map(m => ({
                    role: m.role,
                    content: m.content,
                }));
                Store.currentSessionId = data.session_id;
                break;

            case 'sessions_list':
                Store.sessions = data.sessions || [];
                break;

            case 'pipeline_done':
            case 'pipeline_queued':
                Actions.addChatMessage({
                    role: 'assistant',
                    content: data.message || data.result || '流水线任务已提交',
                });
                Store.chatLoading = false;
                break;

            case 'task_progress':
                // 刷新任务列表
                Actions.fetchTasks();
                break;

            case 'log':
                console.log(`[${data.data?.level}] ${data.data?.message}`);
                break;

            case 'health':
                Store.health = data.data;
                break;

            case 'confirm_modify':
                // 自修改确认对话框 — 目前自动接受
                const accept = confirm(
                    `AI 请求修改文件:\n${data.data?.file}\n\n${data.data?.diff || ''}`
                );
                this.wsSend({
                    type: 'confirm_response',
                    confirm_id: data.data?.confirm_id,
                    accepted: accept,
                });
                break;

            case 'resources':
                Store.resources = data.data || [];
                break;

            case 'jobs':
                // 由 scheduler 页面自行处理
                break;

            case 'status':
                Store.health = data.data;
                break;

            default:
                console.log('未知消息类型:', type, data);
        }
    },

    // ===== 初始化 =====
    init() {
        Router.init();
        this._connectWS();

        // 创建并挂载 Vue 3 应用
        const vueApp = Vue.createApp({
            template: `
<div id="app">
    <div style="display:flex; height:100vh;">
        <Sidebar />
        <main id="main-content">
            <component :is="currentComponent" />
        </main>
    </div>
</div>
            `,

            setup() {
                return {
                    pages,
                    Router,
                    Store,
                    Actions,
                };
            },

            computed: {
                currentComponent() {
                    const map = {
                        dashboard: Dashboard,
                        chat: ChatPanel,
                        resources: ResourceTable,
                        tasks: TaskMonitor,
                        sources: SourceManager,
                        analytics: Analytics,
                        settings: Settings,
                    };
                    return map[Router.current.value] || Dashboard;
                },
            },

            components: {
                Sidebar,
                Dashboard,
                ChatPanel,
                ResourceTable,
                TaskMonitor,
                SourceManager,
                Analytics,
                Settings,
            },

            mounted() {
                // 加载会话列表
                Actions.fetchSessions();
                // 定期刷新
                this._refreshTimer = setInterval(() => {
                    if (Router.current.value === 'dashboard') {
                        Actions.fetchDashboard();
                    }
                }, 30000);
            },

            beforeUnmount() {
                if (this._refreshTimer) clearInterval(this._refreshTimer);
                if (App._reconnectTimer) clearTimeout(App._reconnectTimer);
                if (App._ws) App._ws.close();
            },
        });

        vueApp.mount('#app');
    },
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => App.init());
