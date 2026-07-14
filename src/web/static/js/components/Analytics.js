/**
 * 数据分析组件
 * 趋势图 + 费用统计 + 类型分布
 * 详见架构文档 §21.5 Analytics
 */
const Analytics = {
    template: `
<div class="analytics">
    <!-- 趋势图 (面积) -->
    <div class="glass-card chart-container" style="margin-bottom:1rem;">
        <div class="chart-header">
            <h3 class="chart-title">📈 发布趋势</h3>
            <select class="input-field" v-model="trendDays" @change="loadTrend" style="max-width:120px;">
                <option :value="7">近7天</option>
                <option :value="14">近14天</option>
                <option :value="30">近30天</option>
            </select>
        </div>
        <canvas id="areaChart" style="max-height:260px;"></canvas>
    </div>

    <!-- 类型分布 + 费用 -->
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem;">
        <div class="glass-card chart-container">
            <h3 class="chart-title">🎯 资源类型分布</h3>
            <canvas id="pieChart" style="max-height:220px;"></canvas>
        </div>
        <div class="glass-card chart-container">
            <h3 class="chart-title">💰 费用趋势 (近30天)</h3>
            <canvas id="barChart" style="max-height:220px;"></canvas>
        </div>
    </div>

    <!-- 费用明细 -->
    <div class="glass-card" style="margin-top:1rem;">
        <h3 class="chart-title">💵 费用明细</h3>
        <table class="data-table" style="margin-top:0.5rem;">
            <thead>
                <tr><th>日期</th><th>模型调用</th><th>下载流量</th><th>存储</th><th>合计</th></tr>
            </thead>
            <tbody>
                <tr v-for="row in costDetail" :key="row.date">
                    <td>{{row.date}}</td>
                    <td>¥{{row.model_cost?.toFixed(4) || '0.0000'}}</td>
                    <td>¥{{row.download_cost?.toFixed(4) || '0.0000'}}</td>
                    <td>¥{{row.storage_cost?.toFixed(4) || '0.0000'}}</td>
                    <td style="font-weight:600;">¥{{row.total?.toFixed(4) || '0.0000'}}</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
    `,

    setup() {
        const trendDays = Vue.ref(7);

        async function loadTrend() {
            await Actions.fetchPublishTrend(trendDays.value);
            await Actions.fetchCosts(trendDays.value);
            this.$nextTick(() => this._renderCharts());
        }

        return { Store, Actions, trendDays, loadTrend };
    },

    computed: {
        costDetail() {
            if (!Store.costReport?.daily_breakdown) return [];
            return Store.costReport.daily_breakdown;
        },
    },

    async mounted() {
        await Promise.all([
            Actions.fetchPublishTrend(7),
            Actions.fetchResourceTypes(),
            Actions.fetchCosts(7),
        ]);
        this.$nextTick(() => this._renderCharts());
    },

    watch: {
        'Store.publishTrend'() { this.$nextTick(() => this._renderCharts()); },
        'Store.resourceTypes'() { this.$nextTick(() => this._renderCharts()); },
    },

    methods: {
        _renderCharts() {
            this._renderAreaChart();
            this._renderPieChart();
            this._renderBarChart();
        },

        _renderAreaChart() {
            const canvas = document.getElementById('areaChart');
            if (!canvas || !window.Chart) return;
            const ctx = canvas.getContext('2d');
            if (this._areaInstance) this._areaInstance.destroy();
            this._areaInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: (Store.publishTrend || []).map(t => t.date),
                    datasets: [{
                        label: '发布数',
                        data: (Store.publishTrend || []).map(t => t.count),
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139,92,246,0.15)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#8b5cf6',
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#888' } } },
                    scales: {
                        x: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                        y: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
                    },
                },
            });
        },

        _renderPieChart() {
            const canvas = document.getElementById('pieChart');
            if (!canvas || !window.Chart) return;
            const ctx = canvas.getContext('2d');
            if (this._pieInstance) this._pieInstance.destroy();
            this._pieInstance = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: (Store.resourceTypes || []).map(t => t.name),
                    datasets: [{
                        data: (Store.resourceTypes || []).map(t => t.value),
                        backgroundColor: (Store.resourceTypes || []).map(t => t.color),
                        borderWidth: 2,
                        borderColor: '#1a1a2e',
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#888', usePointStyle: true } } },
                },
            });
        },

        _renderBarChart() {
            const canvas = document.getElementById('barChart');
            if (!canvas || !window.Chart) return;
            const ctx = canvas.getContext('2d');
            if (this._barInstance) this._barInstance.destroy();
            const days = Store.costReport?.daily_breakdown || [];
            this._barInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: days.map(d => d.date),
                    datasets: [{
                        label: '模型费用',
                        data: days.map(d => d.model_cost || 0),
                        backgroundColor: 'rgba(99,102,241,0.6)',
                    }, {
                        label: '下载费用',
                        data: days.map(d => d.download_cost || 0),
                        backgroundColor: 'rgba(139,92,246,0.6)',
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#888', usePointStyle: true } } },
                    scales: {
                        x: { stacked: true, ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                        y: { stacked: true, ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
                    },
                },
            });
        },
    },

    beforeUnmount() {
        if (this._areaInstance) this._areaInstance.destroy();
        if (this._pieInstance) this._pieInstance.destroy();
        if (this._barInstance) this._barInstance.destroy();
    },
};
