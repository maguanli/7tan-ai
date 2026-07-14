/**
 * 响应式状态存储 — Vue 3 reactive
 * 详见架构文档 §21.3
 */
const Store = Vue.reactive({
    // ===== 系统状态 =====
    wsConnected: false,
    wsReconnectAttempts: 0,
    health: null,

    // ===== 仪表盘 =====
    dashboard: {
        totalPublished: 0,
        inProgress: 0,
        thisMonthNew: 0,
        todayCost: 0,
        successRate: 100,
    },

    // ===== 资源 =====
    resources: [],
    resourcesTotal: 0,
    resourcesFilters: {
        type: '',
        status: '',
        search: '',
    },

    // ===== 任务 =====
    activeTasks: [],
    queuedTasks: [],
    allTasks: [],

    // ===== 源站 =====
    sources: [],

    // ===== 对话 =====
    chatMessages: [],
    chatLoading: false,
    currentSessionId: null,
    sessions: [],

    // ===== 设置 =====
    config: {},

    // ===== 统计 =====
    publishTrend: [],
    resourceTypes: [],
    costReport: {},
});

// ===== Actions =====
const Actions = {
    async fetchDashboard() {
        try {
            const r = await fetch('/api/stats/dashboard');
            const d = await r.json();
            Object.assign(Store.dashboard, d);
        } catch (e) { console.error('获取仪表盘失败:', e); }
    },

    async fetchResources(filters = {}) {
        const params = new URLSearchParams({
            limit: 50,
            offset: 0,
            ...filters,
        });
        try {
            const r = await fetch(`/api/resources?${params}`);
            const d = await r.json();
            Store.resources = d.resources || [];
            Store.resourcesTotal = d.total || 0;
        } catch (e) { console.error('获取资源失败:', e); }
    },

    async fetchTasks() {
        try {
            const r = await fetch('/api/tasks');
            const d = await r.json();
            Store.activeTasks = d.active || [];
            Store.queuedTasks = d.queued || [];
            Store.allTasks = d.all || [];
        } catch (e) { console.error('获取任务失败:', e); }
    },

    async fetchSources() {
        try {
            const r = await fetch('/api/sources');
            const d = await r.json();
            Store.sources = d.sources || [];
        } catch (e) { console.error('获取源站失败:', e); }
    },

    async fetchPublishTrend(days = 7) {
        try {
            const r = await fetch(`/api/stats/publish?days=${days}`);
            const d = await r.json();
            Store.publishTrend = d.trend || [];
        } catch (e) { console.error('获取趋势失败:', e); }
    },

    async fetchResourceTypes() {
        try {
            const r = await fetch('/api/stats/types');
            const d = await r.json();
            Store.resourceTypes = d.types || [];
        } catch (e) { console.error('获取类型分布失败:', e); }
    },

    async fetchCosts(days = 30) {
        try {
            const r = await fetch(`/api/stats/costs?days=${days}`);
            const d = await r.json();
            Store.costReport = d;
        } catch (e) { console.error('获取费用失败:', e); }
    },

    async fetchConfig() {
        try {
            const r = await fetch('/api/settings');
            const d = await r.json();
            Store.config = d.settings || {};
        } catch (e) { console.error('获取配置失败:', e); }
    },

    addChatMessage(msg) {
        Store.chatMessages.push(msg);
    },

    clearChat() {
        Store.chatMessages = [];
        Store.currentSessionId = null;
    },

    async fetchSessions() {
        Store.sessions = [];
        try {
            const r = await fetch('/api/chat/history');
            const d = await r.json();
            Store.sessions = d.sessions || [];
        } catch (e) { console.error('获取会话列表失败:', e); }
    },

    async loadSession(sessionId) {
        try {
            const r = await fetch(`/api/chat/history?session_id=${sessionId}`);
            const d = await r.json();
            Store.chatMessages = (d.messages || []).map(m => ({
                role: m.role,
                content: m.content,
            }));
            Store.currentSessionId = sessionId;
        } catch (e) { console.error('加载会话失败:', e); }
    },
};
