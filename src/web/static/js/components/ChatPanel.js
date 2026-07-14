/**
 * AI 对话面板
 * WebSocket 消息收发 + 消息气泡
 * 详见架构文档 §21.4 ChatPanel
 */
const ChatPanel = {
    template: `
<div class="chat-panel" style="display:flex; gap:1rem; height:100%;">
    <!-- 会话列表侧栏 -->
    <div class="glass-card" style="width:200px; flex-shrink:0; overflow-y:auto; display:flex; flex-direction:column;">
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem;">
            <h3 style="margin:0; font-size:0.9rem;">💬 历史会话</h3>
            <button class="btn-icon" @click="Actions.fetchSessions()" title="刷新">
                <i class="fas fa-sync-alt"></i>
            </button>
        </div>
        <div v-if="Store.sessions.length===0" style="padding:1rem; color:#666; font-size:0.8rem; text-align:center;">
            暂无历史会话
        </div>
        <div v-for="s in Store.sessions" :key="s.session_id"
             class="chat-session-item"
             :class="{active: Store.currentSessionId===s.session_id}"
             @click="loadSession(s.session_id)"
             style="padding:0.5rem; cursor:pointer; border-radius:6px; margin:2px 0;"
             :style="Store.currentSessionId===s.session_id ? 'background:rgba(99,102,241,0.3);' : ''">
            <div style="font-size:0.75rem; color:#ccc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                {{s.title}}
            </div>
            <div style="font-size:0.65rem; color:#888;">
                {{s.message_count}}条 · {{s.last_activity?.substring(0,16)}}
            </div>
        </div>
    </div>

    <!-- 聊天区域 -->
    <div style="flex:1; display:flex; flex-direction:column;">
    <div class="glass-card chat-messages" ref="chatBox" style="flex:1;">
        <div v-if="Store.chatMessages.length===0" class="chat-empty">
            <div class="chat-empty-icon">💬</div>
            <p class="chat-empty-title">向 AI 小编发送任务指令</p>
            <p class="chat-empty-hint">例如："爬取3DM最新游戏"、"发布资源到7坛"</p>
            <div class="chat-suggestions">
                <button v-for="s in suggestions" :key="s" class="chat-suggestion-btn"
                        @click="quickSend(s)">{{s}}</button>
            </div>
        </div>

        <div v-for="(msg,i) in Store.chatMessages" :key="i"
             class="chat-msg" :class="msg.role==='user' ? 'chat-user' : 'chat-ai'">
            <div class="chat-msg-header">
                {{msg.role==='user' ? '👤 你' : '🤖 AI小编'}}
            </div>
            <div class="chat-msg-body">{{msg.content}}</div>
            <div v-if="msg.cost" class="chat-msg-cost">💰 ¥{{msg.cost.toFixed(4)}}</div>
        </div>

        <div v-if="Store.chatLoading" class="chat-msg chat-ai">
            <div class="chat-loading">
                <span class="animate-pulse">⏳ AI 思考中...</span>
            </div>
        </div>
    </div>

    <div class="chat-input-row">
        <input class="input-field" v-model="input"
               @keydown.enter.prevent="onEnterKey" placeholder="输入任务指令..."
               :disabled="Store.chatLoading">
        <button class="btn-primary" @click="send"
                :disabled="Store.chatLoading || !input.trim()">
            发送 <i class="fas fa-paper-plane"></i>
        </button>
        <button class="btn-icon" @click="Actions.clearChat()" title="清空对话">
            <i class="fas fa-trash"></i>
        </button>
    </div>
    </div>
</div>
    `,

    setup() {
        const input = Vue.ref('');
        const chatBox = Vue.ref(null);
        const suggestions = [
            '爬取最新游戏资源',
            '查看系统运行状态',
            '分析本月费用',
            '检查源站可用性',
        ];

        function send() {
            const msg = input.value.trim();
            if (!msg || Store.chatLoading) return;
            Actions.addChatMessage({ role: 'user', content: msg });
            input.value = '';
            Store.chatLoading = true;
            App.wsSend({ type: 'chat', message: msg, session_id: Store.currentSessionId });
            Vue.nextTick(() => _scrollBottom());
        }

        function onEnterKey(e) {
            // 兼容输入法：如果正在用中文输入法组合文字，不发送
            if (e.isComposing) return;
            send();
        }

        function quickSend(msg) {
            input.value = msg;
            send();
        }

        function loadSession(sessionId) {
            Actions.loadSession(sessionId);
        }

        function _scrollBottom() {
            if (chatBox.value) {
                chatBox.value.scrollTop = chatBox.value.scrollHeight;
            }
        }

        return { Store, Actions, chatBox, input, suggestions, send, onEnterKey, quickSend, loadSession };
    },
};
