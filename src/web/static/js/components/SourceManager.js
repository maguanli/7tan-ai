/**
 * 源站管理组件
 * CRUD 操作 + 立即爬取
 * 详见架构文档 §21.4 SourceManager
 */
const SourceManager = {
    template: `
<div class="source-manager">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <h3 class="section-title">🌐 源站管理</h3>
        <button class="btn-primary" @click="showAddForm=true">
            <i class="fas fa-plus"></i> 添加源站
        </button>
    </div>

    <!-- 源站卡片 -->
    <div class="source-grid">
        <div v-for="s in Store.sources" :key="s.id" class="glass-card source-card"
             :class="{disabled: !s.enabled}">
            <div class="source-card-header">
                <span class="source-name">{{s.name}}</span>
                <span class="source-type">{{typeLabel(s.site_type)}}</span>
            </div>
            <div class="source-url text-muted">{{s.url}}</div>
            <div class="source-meta">
                <span>间隔: {{s.crawl_interval}}min</span>
                <span>{{s.enabled ? '✅ 启用' : '❌ 禁用'}}</span>
                <span v-if="s.need_login">🔐 需登录</span>
            </div>
            <div class="source-actions">
                <button class="btn-sm" @click="crawlNow(s)">
                    <i class="fas fa-play"></i> 爬取
                </button>
                <button class="btn-sm" @click="editSource(s)">
                    <i class="fas fa-edit"></i> 编辑
                </button>
                <button class="btn-sm btn-danger" @click="deleteSource(s)">
                    <i class="fas fa-trash"></i> 删除
                </button>
            </div>
        </div>
    </div>

    <!-- 添加/编辑表单 -->
    <div v-if="showAddForm || editingSource" class="modal-overlay" @click.self="closeForm">
        <div class="modal glass-card" style="max-width:500px;">
            <h3>{{editingSource ? '✏️ 编辑源站' : '➕ 添加源站'}}</h3>
            <div class="form-group">
                <label>名称 *</label>
                <input class="input-field" v-model="form.name">
            </div>
            <div class="form-group">
                <label>URL *</label>
                <input class="input-field" v-model="form.url">
            </div>
            <div class="form-group">
                <label>类型</label>
                <select class="input-field" v-model="form.site_type">
                    <option value="game">游戏</option>
                    <option value="software">软件</option>
                </select>
            </div>
            <div class="form-group" style="display:flex; gap:1rem;">
                <div style="flex:1;">
                    <label>爬取间隔(分)</label>
                    <input class="input-field" type="number" v-model.number="form.crawl_interval">
                </div>
                <div style="flex:1; display:flex; align-items:flex-end;">
                    <label style="display:flex; align-items:center; gap:0.5rem;">
                        <input type="checkbox" v-model="form.enabled">
                        启用
                    </label>
                </div>
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" v-model="form.need_login">
                    需要登录
                </label>
            </div>
            <template v-if="form.need_login">
                <div class="form-group">
                    <label>登录 URL</label>
                    <input class="input-field" v-model="form.login_url">
                </div>
                <div class="form-group">
                    <label>用户名</label>
                    <input class="input-field" v-model="form.login_username">
                </div>
                <div class="form-group">
                    <label>密码</label>
                    <input class="input-field" type="password" v-model="form.login_password">
                </div>
            </template>
            <div class="form-group">
                <label>备注</label>
                <textarea class="input-field" v-model="form.notes" rows="2"></textarea>
            </div>
            <div style="display:flex; gap:0.5rem; justify-content:flex-end;">
                <button class="btn-primary" @click="saveSource">保存</button>
                <button class="btn-secondary" @click="closeForm">取消</button>
            </div>
        </div>
    </div>
</div>
    `,

    setup() {
        const showAddForm = Vue.ref(false);
        const editingSource = Vue.ref(null);
        const form = Vue.ref({});

        function resetForm() {
            form.value = {
                name: '', url: '', site_type: 'game',
                crawl_interval: 360, enabled: true, need_login: false,
                login_url: '', login_username: '', login_password: '', notes: '',
            };
        }

        function editSource(s) {
            editingSource.value = s;
            form.value = { ...s };
            form.value.need_login = !!s.need_login;
        }

        function closeForm() {
            showAddForm.value = false;
            editingSource.value = null;
        }

        async function saveSource() {
            try {
                if (editingSource.value) {
                    await fetch(`/api/sources/${editingSource.value.id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(form.value),
                    });
                } else {
                    await fetch('/api/sources', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(form.value),
                    });
                }
                closeForm();
                Actions.fetchSources();
            } catch (e) { console.error('保存失败:', e); }
        }

        async function deleteSource(s) {
            if (!confirm(`确认删除源站 "${s.name}"?`)) return;
            await fetch(`/api/sources/${s.id}`, { method: 'DELETE' });
            Actions.fetchSources();
        }

        async function crawlNow(s) {
            try {
                await fetch(`/api/sources/${s.id}/crawl`, { method: 'POST' });
                alert(`已提交爬取任务: ${s.name}`);
            } catch (e) { alert('爬取失败: ' + e); }
        }

        function typeLabel(t) {
            return t === 'game' ? '🎮 游戏' : t === 'software' ? '💻 软件' : t;
        }

        resetForm();

        return { Store, Actions, showAddForm, editingSource, form,
                 editSource, closeForm, saveSource, deleteSource, crawlNow, typeLabel };
    },

    mounted() {
        Actions.fetchSources();
    },
};
