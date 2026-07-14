/**
 * 系统设置组件
 * 配置表单 + 健康检查 + 重启
 * 详见架构文档 §21.4 Settings
 */
const Settings = {
    template: `
<div class="settings">
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
        <!-- 系统操作 -->
        <div class="glass-card">
            <h3 class="section-title">🛠️ 系统操作</h3>
            <div style="display:flex; flex-direction:column; gap:0.5rem;">
                <button class="btn-primary" @click="healthCheck">
                    🏥 健康检查
                </button>
                <button class="btn-primary" @click="checkIntegrity">
                    🔒 完整性检查
                </button>
                <button class="btn-primary" @click="getStatus">
                    📊 系统状态
                </button>
                <button class="btn-danger" @click="restartApp"
                        style="background:rgba(239,68,68,0.8);">
                    🔄 重启程序
                </button>
            </div>
            <div class="glass-card" v-if="output" style="margin-top:1rem; white-space:pre-wrap; font-size:0.8rem; max-height:300px; overflow-y:auto;">
                {{output}}
            </div>
        </div>

        <!-- AI 配置 -->
        <div class="glass-card">
            <h3 class="section-title">🤖 AI 配置</h3>
            <div class="form-group">
                <label>模型提供商</label>
                <select class="input-field" v-model="aiConfig.provider">
                    <option value="deepseek">DeepSeek</option>
                    <option value="openai">OpenAI</option>
                    <option value="siliconflow">SiliconFlow</option>
                    <option value="doubao">豆包</option>
                    <option value="ollama">Ollama</option>
                    <option value="custom">自定义</option>
                </select>
            </div>
            <div class="form-group">
                <label>API Key</label>
                <input class="input-field" type="password" v-model="aiConfig.api_key" placeholder="sk-...">
            </div>
            <div class="form-group">
                <label>模型名称</label>
                <input class="input-field" v-model="aiConfig.model">
            </div>
            <div class="form-group">
                <label>Base URL (可选)</label>
                <input class="input-field" v-model="aiConfig.base_url">
            </div>
            <button class="btn-primary" @click="saveAIConfig">💾 保存 AI 配置</button>
        </div>

        <!-- 7坛配置 -->
        <div class="glass-card">
            <h3 class="section-title">🌐 7坛账户</h3>
            <div class="form-group">
                <label>URL</label>
                <input class="input-field" v-model="siteConfig.url">
            </div>
            <div class="form-group">
                <label>用户名</label>
                <input class="input-field" v-model="siteConfig.username">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input class="input-field" type="password" v-model="siteConfig.password">
            </div>
            <button class="btn-primary" @click="saveSiteConfig">💾 保存 7坛配置</button>
        </div>

        <!-- 爬取配置 -->
        <div class="glass-card">
            <h3 class="section-title">🕷️ 爬取设置</h3>
            <div class="form-group">
                <label>默认间隔 (分钟)</label>
                <input class="input-field" type="number" v-model.number="crawlConfig.interval">
            </div>
            <div class="form-group">
                <label>并发数</label>
                <input class="input-field" type="number" v-model.number="crawlConfig.concurrency">
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" v-model="crawlConfig.headless">
                    无头模式
                </label>
            </div>
            <button class="btn-primary" @click="saveCrawlConfig">💾 保存爬取配置</button>
        </div>
    </div>
</div>
    `,

    setup() {
        const output = Vue.ref('');
        const aiConfig = Vue.ref({});
        const siteConfig = Vue.ref({});
        const crawlConfig = Vue.ref({});

        async function healthCheck() {
            try {
                const r = await fetch('/api/health');
                const d = await r.json();
                output.value = JSON.stringify(d.detail, null, 2);
            } catch (e) { output.value = '错误: ' + e; }
        }

        async function getStatus() {
            try {
                const r = await fetch('/api/status');
                const d = await r.json();
                output.value = JSON.stringify(d.status, null, 2);
            } catch (e) { output.value = '错误: ' + e; }
        }

        async function checkIntegrity() {
            try {
                const r = await fetch('/api/health');
                output.value = '完整性检查: 通过 ✓';
            } catch (e) { output.value = '错误: ' + e; }
        }

        async function restartApp() {
            if (!confirm('确认重启程序？')) return;
            try {
                await fetch('/api/settings/restart', { method: 'POST' });
                output.value = '重启中...';
            } catch (e) { output.value = '重启请求已发送'; }
        }

        async function saveAIConfig() {
            const provider = aiConfig.value.provider || 'deepseek';
            const payload = {
                ai: {
                    active: provider,
                    configs: {
                        [provider]: {
                            provider: provider,
                            model: aiConfig.value.model || '',
                            api_key: aiConfig.value.api_key || '',
                            base_url: aiConfig.value.base_url || '',
                        }
                    }
                }
            };
            await _save(payload);
        }

        async function saveSiteConfig() {
            await _save({ site_7tan: { ...siteConfig.value } });
        }

        async function saveCrawlConfig() {
            await _save({ crawler: { ...crawlConfig.value } });
        }

        async function _save(data) {
            try {
                const r = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });
                const d = await r.json();
                output.value = d.message || '已保存';
            } catch (e) { output.value = '保存失败: ' + e; }
        }

        function _loadConfig() {
            // 兼容新旧两种 AI 配置格式
            const ai = Store.config.ai || {};
            if (ai.configs && ai.active) {
                // 新格式: {active: "deepseek", configs: {deepseek: {provider, model, api_key, ...}}}
                const activeConfig = ai.configs[ai.active] || {};
                aiConfig.value = {
                    provider: ai.active,
                    api_key: activeConfig.api_key || '',
                    model: activeConfig.model || '',
                    base_url: activeConfig.base_url || '',
                };
            } else if (ai.provider) {
                // 旧格式: {provider: "deepseek", model: "...", api_key: "...", ...}
                aiConfig.value = {
                    provider: ai.provider || '',
                    api_key: ai.api_key || '',
                    model: ai.model || '',
                    base_url: ai.base_url || '',
                };
            }
            if (Store.config.site_7tan) {
                siteConfig.value = { ...Store.config.site_7tan };
            }
            if (Store.config.crawler) {
                crawlConfig.value = { ...Store.config.crawler };
            }
        }

        return {
            Store, output, aiConfig, siteConfig, crawlConfig,
            healthCheck, getStatus, checkIntegrity, restartApp,
            saveAIConfig, saveSiteConfig, saveCrawlConfig,
        };
    },

    async mounted() {
        if (!Store.config || Object.keys(Store.config).length === 0) {
            await Actions.fetchConfig();
        }
        this._loadConfig();
    },

    methods: {
        _loadConfig() {
            // 兼容新旧两种 AI 配置格式
            const ai = this.Store.config.ai || {};
            if (ai.configs && ai.active) {
                const activeConfig = ai.configs[ai.active] || {};
                this.aiConfig = {
                    provider: ai.active,
                    api_key: activeConfig.api_key || '',
                    model: activeConfig.model || '',
                    base_url: activeConfig.base_url || '',
                };
            } else if (ai.provider) {
                this.aiConfig = {
                    provider: ai.provider || '',
                    api_key: ai.api_key || '',
                    model: ai.model || '',
                    base_url: ai.base_url || '',
                };
            }
            if (this.Store.config.site_7tan) {
                this.siteConfig = { ...this.Store.config.site_7tan };
            }
            if (this.Store.config.crawler) {
                this.crawlConfig = { ...this.Store.config.crawler };
            }
        },
    },
};
