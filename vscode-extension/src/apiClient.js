/**
 * 7Tan API 客户端
 * 与本地 7Tan 服务 (localhost:9800) 通信
 */

const http = require('http');
const https = require('https');

class ApiClient {
    /**
     * @param {string} baseUrl - 7Tan API 地址，如 http://localhost:9800
     */
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    /**
     * 健康检查
     * @returns {Promise<boolean>}
     */
    async healthCheck() {
        try {
            const result = await this._get('/api/health');
            return result && result.status === 'ok';
        } catch {
            return false;
        }
    }

    /**
     * 发送对话消息
     * @param {string} message - 用户消息
     * @param {string} [sessionId] - 会话 ID（可选，不传则创建新会话）
     * @param {string} [model] - 模型名称（可选）
     * @returns {Promise<{session_id: string, success: boolean, result: string, cost: number}>}
     */
    async sendMessage(message, sessionId = null, model = null) {
        const body = {
            message: message,
            session_id: sessionId,
            model: model
        };

        return this._post('/api/chat/send', body);
    }

    /**
     * 获取对话历史
     * @param {string} [sessionId] - 会话 ID（可选，不传则获取所有会话）
     * @returns {Promise<Object>}
     */
    async getHistory(sessionId = null) {
        const path = sessionId
            ? `/api/chat/history?session_id=${encodeURIComponent(sessionId)}`
            : '/api/chat/history';
        return this._get(path);
    }

    /**
     * 删除会话
     * @param {string} sessionId
     * @returns {Promise<Object>}
     */
    async deleteSession(sessionId) {
        return this._delete(`/api/chat/session/${encodeURIComponent(sessionId)}`);
    }

    /**
     * 获取版本信息
     * @returns {Promise<Object>}
     */
    async getVersion() {
        return this._get('/api/version');
    }

    // ===== 内部 HTTP 方法 =====

    /**
     * HTTP GET
     * @param {string} path
     * @returns {Promise<any>}
     */
    _get(path) {
        return new Promise((resolve, reject) => {
            const url = new URL(path, this.baseUrl);
            const options = {
                hostname: url.hostname,
                port: url.port,
                path: url.pathname + url.search,
                method: 'GET',
                headers: { 'Accept': 'application/json' },
                timeout: 30000
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch {
                        resolve(data);
                    }
                });
            });

            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });
            req.end();
        });
    }

    /**
     * HTTP POST
     * @param {string} path
     * @param {Object} body
     * @returns {Promise<any>}
     */
    _post(path, body) {
        return new Promise((resolve, reject) => {
            const url = new URL(path, this.baseUrl);
            const jsonBody = JSON.stringify(body);
            const options = {
                hostname: url.hostname,
                port: url.port,
                path: url.pathname + url.search,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Content-Length': Buffer.byteLength(jsonBody)
                },
                timeout: 120000  // 2分钟超时（AI 回复可能较慢）
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch {
                        resolve(data);
                    }
                });
            });

            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });
            req.write(jsonBody);
            req.end();
        });
    }

    /**
     * HTTP DELETE
     * @param {string} path
     * @returns {Promise<any>}
     */
    _delete(path) {
        return new Promise((resolve, reject) => {
            const url = new URL(path, this.baseUrl);
            const options = {
                hostname: url.hostname,
                port: url.port,
                path: url.pathname + url.search,
                method: 'DELETE',
                headers: { 'Accept': 'application/json' },
                timeout: 10000
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch {
                        resolve(data);
                    }
                });
            });

            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });
            req.end();
        });
    }
}

module.exports = { ApiClient };
