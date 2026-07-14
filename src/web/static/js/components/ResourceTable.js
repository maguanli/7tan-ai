/**
 * 资源管理表格
 * 筛选/搜索/分页
 * 详见架构文档 §21.4 ResourceTable
 */
const ResourceTable = {
    template: `
<div class="resource-table">
    <!-- 工具栏 -->
    <div class="resource-toolbar glass-card">
        <input class="input-field" v-model="search" @input="onSearch" placeholder="🔍 搜索标题..."
               style="max-width:240px;">
        <select class="input-field" v-model="typeFilter" @change="onFilter" style="max-width:140px;">
            <option value="">全部类型</option>
            <option value="game">🎮 游戏</option>
            <option value="software">💻 软件</option>
        </select>
        <select class="input-field" v-model="statusFilter" @change="onFilter" style="max-width:140px;">
            <option value="">全部状态</option>
            <option value="published">✅ 已发布</option>
            <option value="pending">⏳ 待处理</option>
            <option value="downloading">⬇️ 下载中</option>
            <option value="rewriting">✏️ 改写中</option>
            <option value="uploading">⬆️ 上传中</option>
            <option value="failed">❌ 失败</option>
        </select>
        <div style="flex:1;"></div>
        <button class="btn-primary" @click="refresh" style="padding:8px 16px;">
            <i class="fas fa-sync-alt"></i> 刷新
        </button>
    </div>

    <!-- 表格 -->
    <div class="glass-card resource-list">
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>类型</th>
                    <th>标题</th>
                    <th>版本</th>
                    <th>源站</th>
                    <th>状态</th>
                    <th>时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="r in Store.resources" :key="r.id" class="data-row">
                    <td class="text-muted">#{{r.id}}</td>
                    <td>{{r.resource_type === 'game' ? '🎮' : '💻'}}</td>
                    <td>
                        <div>{{r.title}}</div>
                        <div v-if="r.final_title && r.final_title!==r.title" class="text-muted" style="font-size:0.7rem;">
                            → {{r.final_title}}
                        </div>
                    </td>
                    <td>v{{r.version || '?'}}</td>
                    <td class="text-muted" style="font-size:0.8rem;">{{r.source_site || '-'}}</td>
                    <td><span class="status-badge" :class="statusClass(r.status)">{{statusLabel(r.status)}}</span></td>
                    <td class="text-muted" style="font-size:0.75rem;">{{formatDate(r.created_at)}}</td>
                    <td>
                        <button class="btn-sm" @click="viewDetail(r)" title="详情">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn-sm btn-danger" @click="deleteResource(r)" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            </tbody>
        </table>
        <div v-if="Store.resources.length===0" class="empty-state">
            <div style="font-size:2rem;">📭</div>
            <p>暂无资源</p>
        </div>

        <!-- 分页 -->
        <div v-if="Store.resourcesTotal > 50" class="pagination">
            <button class="btn-sm" :disabled="offset===0" @click="prevPage">上一页</button>
            <span class="text-muted">{{offset+1}}-{{offset+Store.resources.length}} / {{Store.resourcesTotal}}</span>
            <button class="btn-sm" :disabled="offset+50>=Store.resourcesTotal" @click="nextPage">下一页</button>
        </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailResource" class="modal-overlay" @click.self="detailResource=null">
        <div class="modal glass-card">
            <h3>📋 资源详情</h3>
            <div class="detail-grid">
                <div v-for="(v,k) in detailResource" :key="k" class="detail-item">
                    <span class="detail-key">{{k}}:</span>
                    <span class="detail-value">{{v}}</span>
                </div>
            </div>
            <button class="btn-primary" @click="detailResource=null">关闭</button>
        </div>
    </div>
</div>
    `,

    setup() {
        const search = Vue.ref('');
        const typeFilter = Vue.ref('');
        const statusFilter = Vue.ref('');
        const detailResource = Vue.ref(null);
        const offset = Vue.ref(0);
        let _searchTimer = null;

        function refresh() {
            Actions.fetchResources({
                search: search.value,
                resource_type: typeFilter.value,
                status: statusFilter.value,
            });
        }

        function onSearch() {
            clearTimeout(_searchTimer);
            _searchTimer = setTimeout(() => refresh(), 300);
        }

        function onFilter() { refresh(); }

        function prevPage() {
            offset.value = Math.max(0, offset.value - 50);
            refresh();
        }

        function nextPage() {
            offset.value += 50;
            refresh();
        }

        function viewDetail(resource) {
            detailResource.value = resource;
        }

        async function deleteResource(resource) {
            if (!confirm(`确认删除 "${resource.title}"?`)) return;
            try {
                await fetch(`/api/resources/${resource.id}`, { method: 'DELETE' });
                refresh();
            } catch (e) { console.error('删除失败:', e); }
        }

        function statusClass(s) {
            const map = {
                published: 'status-published', pending: 'status-pending',
                failed: 'status-failed', downloading: 'status-downloading',
            };
            return map[s] || 'status-pending';
        }

        function statusLabel(s) {
            const map = {
                published: '已发布', pending: '待处理', failed: '失败',
                downloading: '下载中', rewriting: '改写中', uploading: '上传中',
                publishing: '发布中',
            };
            return map[s] || s;
        }

        function formatDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('zh-CN');
        }

        return {
            Store, Actions, search, typeFilter, statusFilter, detailResource, offset,
            refresh, onSearch, onFilter, prevPage, nextPage,
            viewDetail, deleteResource, statusClass, statusLabel, formatDate,
        };
    },

    mounted() {
        Actions.fetchResources();
    },
};
