/**
 * 任务监控组件
 * 活跃任务 + 队列状态 + 历史日志
 * 详见架构文档 §21.4 TaskMonitor
 */
const TaskMonitor = {
    template: `
<div class="task-monitor">
    <!-- 概览 -->
    <div class="stat-cards">
        <div class="stat-card">
            <div class="stat-icon" style="background:rgba(59,130,246,0.15);">▶️</div>
            <div class="stat-info">
                <div class="stat-value">{{activeCount}}</div>
                <div class="stat-label">活跃任务</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon" style="background:rgba(234,179,8,0.15);">⏳</div>
            <div class="stat-info">
                <div class="stat-value">{{queuedCount}}</div>
                <div class="stat-label">排队中</div>
            </div>
        </div>
    </div>

    <!-- 活跃任务列表 -->
    <div class="glass-card" style="margin-top:1rem;">
        <h3 class="section-title">▶️ 活跃任务</h3>
        <div v-if="Store.activeTasks.length===0" class="empty-state">
            <p>暂无活跃任务</p>
        </div>
        <div v-for="task in Store.activeTasks" :key="task.id" class="task-item">
            <div class="task-header">
                <span class="task-name">{{task.name}}</span>
                <span class="task-priority" :class="'priority-'+task.priority">
                    {{priorityLabel(task.priority)}}
                </span>
            </div>
            <div class="task-progress-bar">
                <div class="task-progress-fill" :style="{width: (task.progress||0)+'%'}"></div>
            </div>
            <div class="task-footer">
                <span class="text-muted" style="font-size:0.75rem;">{{task.status || 'running'}}</span>
                <button class="btn-sm btn-danger" @click="cancelTask(task.id)">取消</button>
            </div>
        </div>
    </div>

    <!-- 等待队列 -->
    <div class="glass-card" style="margin-top:1rem;">
        <h3 class="section-title">⏳ 等待队列</h3>
        <div v-if="Store.queuedTasks.length===0" class="empty-state">
            <p>队列为空</p>
        </div>
        <div v-for="task in Store.queuedTasks" :key="task.id" class="queue-item">
            <span>{{task.name}}</span>
            <span class="text-muted" style="font-size:0.75rem;">优先级: {{priorityLabel(task.priority)}}</span>
        </div>
    </div>

    <!-- 刷新按钮 -->
    <div style="margin-top:1rem; text-align:center;">
        <button class="btn-primary" @click="refresh">
            <i class="fas fa-sync-alt"></i> 刷新
        </button>
    </div>
</div>
    `,

    setup() {
        function refresh() { Actions.fetchTasks(); }
        async function cancelTask(taskId) {
            try {
                await fetch(`/api/tasks/${taskId}/cancel`, { method: 'POST' });
                refresh();
            } catch (e) { console.error('取消任务失败:', e); }
        }

        function priorityLabel(p) {
            const map = { 1: '高', 2: '中', 3: '低' };
            return map[p] || '中';
        }

        return { Store, Actions, refresh, cancelTask, priorityLabel };
    },

    computed: {
        activeCount() { return Store.activeTasks?.length || 0; },
        queuedCount() { return Store.queuedTasks?.length || 0; },
    },

    mounted() {
        Actions.fetchTasks();
    },
};
