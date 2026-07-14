/**
 * 仪表盘组件
 * 4 张统计卡片 + 趋势图 + 类型分布
 * 详见架构文档 §21.5 Dashboard
 */
const Dashboard = {
    template: `
<div class="dashboard">
    <!-- 统计卡片 -->
    <div class="stat-cards">
        <div class="stat-card">
            <div class="stat-icon" style="background:rgba(34,197,94,0.15);">📦</div>
            <div class="stat-info">
                <div class="stat-value">{{Store.dashboard.totalPublished}}</div>
                <div class="stat-label">已发布资源</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon" style="background:rgba(59,130,246,0.15);">⚙️</div>
            <div class="stat-info">
                <div class="stat-value">{{Store.dashboard.inProgress}}</div>
                <div class="stat-label">处理中</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon" style="background:rgba(234,179,8,0.15);">🆕</div>
            <div class="stat-info">
                <div class="stat-value">{{Store.dashboard.thisMonthNew}}</div>
                <div class="stat-label">本月新增</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon" style="background:rgba(239,68,68,0.15);">💰</div>
            <div class="stat-info">
                <div class="stat-value">¥{{Store.dashboard.todayCost?.toFixed(2) || '0.00'}}</div>
                <div class="stat-label">今日费用</div>
            </div>
        </div>
    </div>

    <!-- 图表区 -->
    <div style="display:grid; grid-template-columns:2fr 1fr; gap:1rem; margin-top:1rem;">
        <div class="glass-card chart-container">
            <h3 class="chart-title">📈 发布趋势 (近7天)</h3>
            <canvas id="trendChart" style="max-height:220px;"></canvas>
        </div>
        <div class="glass-card chart-container">
            <h3 class="chart-title">🎯 资源类型分布</h3>
            <canvas id="typeChart" style="max-height:220px;"></canvas>
        </div>
    </div>

    <!-- 成功率 + 健康状态 -->
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:1rem;">
        <div class="glass-card">
            <div style="text-align:center;">
                <div style="font-size:2.5rem; font-weight:700; color:#4ade80;">{{Store.dashboard.successRate}}%</div>
                <div style="color:#888; font-size:0.85rem;">成功率</div>
            </div>
        </div>
        <div class="glass-card">
            <div style="display:flex; gap:1rem; justify-content:center;">
                <div style="text-align:center;">
                    <div style="color:#888; font-size:0.75rem;">CPU</div>
                    <div style="font-weight:600;">{{Store.health?.cpu_percent || 0}}%</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#888; font-size:0.75rem;">内存</div>
                    <div style="font-weight:600;">{{Store.health?.memory_percent || 0}}%</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#888; font-size:0.75rem;">磁盘</div>
                    <div style="font-weight:600;">{{Store.health?.disk_percent || 0}}%</div>
                </div>
            </div>
        </div>
    </div>
</div>
    `,
    setup() {},

    async mounted() {
        await Promise.all([
            Actions.fetchDashboard(),
            Actions.fetchPublishTrend(7),
            Actions.fetchResourceTypes(),
        ]);
        this.$nextTick(() => this._renderCharts());
    },

    watch: {
        'Store.publishTrend'() { this.$nextTick(() => this._renderCharts()); },
        'Store.resourceTypes'() { this.$nextTick(() => this._renderCharts()); },
    },

    methods: {
        _renderCharts() {
            this._renderTrendChart();
            this._renderTypeChart();
        },

        _renderTrendChart() {
            const canvas = document.getElementById('trendChart');
            if (!canvas || !window.Chart) return;
            const ctx = canvas.getContext('2d');
            if (this._trendChartInstance) this._trendChartInstance.destroy();
            this._trendChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: (Store.publishTrend || []).map(t => t.date),
                    datasets: [{
                        label: '发布数',
                        data: (Store.publishTrend || []).map(t => t.count),
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99,102,241,0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointBackgroundColor: '#6366f1',
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                        y: { ticks: { color: '#888', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true },
                    },
                },
            });
        },

        _renderTypeChart() {
            const canvas = document.getElementById('typeChart');
            if (!canvas || !window.Chart) return;
            const ctx = canvas.getContext('2d');
            if (this._typeChartInstance) this._typeChartInstance.destroy();
            this._typeChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: (Store.resourceTypes || []).map(t => t.name),
                    datasets: [{
                        data: (Store.resourceTypes || []).map(t => t.value),
                        backgroundColor: (Store.resourceTypes || []).map(t => t.color || '#6366f1'),
                        borderWidth: 2,
                        borderColor: '#1a1a2e',
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#888', padding: 16, usePointStyle: true } } },
                },
            });
        },
    },

    beforeUnmount() {
        if (this._trendChartInstance) this._trendChartInstance.destroy();
        if (this._typeChartInstance) this._typeChartInstance.destroy();
    },
};
