/**
 * 侧边栏组件
 * 导航菜单 + 连接状态指示
 * 详见架构文档 §21.4 Sidebar
 */
const Sidebar = {
    template: `
<aside class="glass" id="sidebar">
    <div class="sidebar-header">
        <span class="sidebar-logo">🤖</span>
        <span class="sidebar-title">7坛AI小编</span>
    </div>

    <nav class="sidebar-nav">
        <div v-for="p in pages" :key="p.id"
             class="sidebar-item"
             :class="{active: Router.current.value===p.id}"
             @click="Router.navigate(p.id)">
            <i :class="p.icon" class="sidebar-item-icon"></i>
            <span class="sidebar-item-label">{{p.label}}</span>
            <span v-if="p.badge" class="sidebar-badge">{{p.badge}}</span>
        </div>
    </nav>

    <div class="sidebar-footer">
        <div class="sidebar-status">
            <span class="status-dot" :class="{connected: Store.wsConnected}"></span>
            <span class="status-text">{{Store.wsConnected ? '已连接' : '断线重连...'}}</span>
        </div>
        <div class="sidebar-version">v5.1.0 · :9800</div>
    </div>
</aside>
    `,
    setup() {
        return { pages, Router, Store };
    },
};
