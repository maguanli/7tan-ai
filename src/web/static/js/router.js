/**
 * 简易 Hash 路由器
 * 管理 7 个页面的切换
 * 详见架构文档 §21.2
 */

const pages = [
    { id: 'dashboard', label: '仪表盘', icon: 'fas fa-chart-pie' },
    { id: 'chat',     label: 'AI 对话', icon: 'fas fa-comments' },
    { id: 'resources',label: '资源管理', icon: 'fas fa-layer-group' },
    { id: 'tasks',    label: '任务监控', icon: 'fas fa-list-check' },
    { id: 'sources',  label: '源站管理', icon: 'fas fa-globe' },
    { id: 'analytics',label: '数据分析', icon: 'fas fa-chart-line' },
    { id: 'settings', label: '系统设置', icon: 'fas fa-sliders' },
];

const Router = {
    current: Vue.ref('dashboard'),

    init() {
        // 监听 hash 变化
        const hash = window.location.hash.replace('#', '');
        if (hash && pages.find(p => p.id === hash)) {
            this.current.value = hash;
        }

        window.addEventListener('hashchange', () => {
            const newHash = window.location.hash.replace('#', '');
            if (newHash && pages.find(p => p.id === newHash)) {
                this.current.value = newHash;
            }
        });
    },

    navigate(pageId) {
        this.current.value = pageId;
        window.location.hash = pageId;
    },
};
