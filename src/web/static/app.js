/* ===== 7Tan 网页控制面板 — 前端逻辑（原生 JS，零依赖） ===== */
"use strict";

/* ---------- 工具 ---------- */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function fmtSize(b) {
  if (b == null || isNaN(b)) return "-";
  if (b === 0) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return b.toFixed(b >= 100 || i === 0 ? 0 : 1) + " " + u[i];
}

function fmtTime(t) {
  if (!t) return "-";
  return String(t).replace("T", " ").slice(0, 19);
}

let toastTimer = null;
function toast(msg, isErr) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast show" + (isErr ? " err" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

/* 轻量 Markdown 渲染（代码块 / 行内代码 / 加粗 / 换行） */
function renderMarkdown(text) {
  let s = escapeHtml(text == null ? "" : text);
  s = s.replace(/```(\w*)\n?([\s\S]*?)```/g, (m, lang, code) => `<pre class="code-block">${code}</pre>`);
  s = s.replace(/`([^`\n]+)`/g, (m, code) => `<code>${code}</code>`);
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\n/g, "<br>");
  return s;
}

/* ---------- API 封装 ---------- */
const API = {
  token: localStorage.getItem("7tan_web_token") || "",
  async req(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (this.token) headers["Authorization"] = "Bearer " + this.token;
    const resp = await fetch(path, {
      method,
      headers,
      body: body != null ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) {
      let msg = "HTTP " + resp.status;
      try { const j = await resp.json(); msg = j.detail || j.error || msg; } catch (e) {}
      throw new Error(msg);
    }
    return resp.json();
  },
  get(path) { return this.req("GET", path); },
  post(path, body) { return this.req("POST", path, body || {}); },
  put(path, body) { return this.req("PUT", path, body || {}); },
  del(path) { return this.req("DELETE", path); },
};

/* ---------- WebSocket（实时广播） ---------- */
let ws = null, wsRetry = 0;
function connectWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = proto + "//" + location.host + "/ws" +
    (API.token ? "?token=" + encodeURIComponent(API.token) : "");
  try { ws = new WebSocket(url); } catch (e) { scheduleReconnect(); return; }
  ws.onopen = () => {
    wsRetry = 0;
    $("#connDot").classList.add("on");
    $("#connText").textContent = "已连接";
  };
  ws.onclose = () => {
    $("#connDot").classList.remove("on");
    $("#connText").textContent = "已断开";
    scheduleReconnect();
  };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      onWSMessage(msg);
    } catch (e) {}
  };
}
function scheduleReconnect() {
  wsRetry++;
  const delay = Math.min(30000, 2000 * Math.pow(1.6, wsRetry));
  setTimeout(connectWS, delay);
}
function onWSMessage(msg) {
  const t = msg.type || "";
  if (t === "task_progress" || t === "progress") {
    const d = msg.data || {};
    toast("⏳ " + (d.message || d.task || "任务进行中…"));
    if (currentView === "tasks" || currentView === "dashboard") refreshCurrent();
  } else if (t === "status") {
    if (currentView === "dashboard") renderDashboard(undefined, msg.data);
  } else if (t === "chat_done") {
    toast("✅ 对话完成");
    if (currentView === "chat") loadChatHistory(curSession);
  } else if (t === "chat_error") {
    toast("❌ " + (msg.error || "对话出错"), true);
  } else if (t === "log") {
    const d = msg.data || {};
    appendConsole(d.message || "");
  } else if (t === "sessions" || t === "jobs" || t === "resources") {
    if (currentView === "chat" && t === "sessions") loadSessions();
  }
}

/* ---------- 视图切换 ---------- */
let currentView = "chat";
$$(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});
function switchView(view) {
  currentView = view;
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + view));
  refreshCurrent();
}
function refreshCurrent() {
  const fns = {
    dashboard: loadDashboard, resources: loadResources,
    tasks: loadTasks, chat: () => { loadSessions(); if (curSession) loadChatHistory(curSession); loadChatConsole(); },
    sources: loadSources, settings: loadSettings, plugins: loadMarketPlugins,
    code: loadCodeChanges, editor: edRender, terminal: () => {}, logs: loadLogs, update: loadUpdate,
  };
  if (fns[currentView]) fns[currentView]();
}

/* ---------- Token ---------- */
$("#tokenInput").value = API.token;
$("#tokenBtn").addEventListener("click", () => {
  API.token = $("#tokenInput").value.trim();
  localStorage.setItem("7tan_web_token", API.token);
  toast("✅ Token 已保存");
  try { ws && ws.close(); } catch (e) {}
  connectWS();
  refreshCurrent();
});
$("#connInfo").textContent = location.host;

/* ---------- 授权状态 ---------- */
async function loadLicenseStatus() {
  try {
    const d = await API.get("/api/license/status");
    const el = $("#proBadge");
    el.textContent = d.is_pro ? "👑 完整版已激活" : "🆓 免费版";
    el.classList.toggle("pro", !!d.is_pro);
  } catch (e) { $("#proBadge").textContent = "授权状态不可用"; }
}

/* ---------- 仪表盘 ---------- */
async function loadDashboard() {
  try {
    const d = await API.get("/api/stats/dashboard");
    renderDashboard(d);
  } catch (e) { toast("仪表盘加载失败: " + e.message, true); }
}
async function renderDashboard(d, wsStatus) {
  const cards = [
    { cls: "green", lbl: "已发布", num: d.total_published ?? "-" },
    { cls: "blue", lbl: "处理中", num: d.in_progress ?? "-" },
    { cls: "violet", lbl: "本月新增", num: d.this_month_new ?? "-" },
    { cls: "yellow", lbl: "今日费用(元)", num: d.today_cost ?? "-" },
    { cls: "green", lbl: "成功率", num: (d.success_rate ?? "-") + "%" },
  ];
  $("#dashCards").innerHTML = cards.map((c) =>
    `<div class="card ${c.cls}"><div class="lbl">${c.lbl}</div><div class="num">${escapeHtml(c.num)}</div></div>`
  ).join("");

  // 系统状态（WS 推送的 status 优先）
  const sys = d.system || wsStatus;
  if (sys) {
    $("#dashSystem").textContent = JSON.stringify(sys, null, 2);
  } else {
    try {
      const s = await API.get("/api/status");
      $("#dashSystem").textContent = JSON.stringify(s, null, 2);
    } catch (e) {
      $("#dashSystem").textContent = "（系统状态不可用）";
    }
  }

  // 趋势
  try {
    const t = await API.get("/api/stats/publish?days=7");
    const trend = (t.trend || []).map((x) => x.count);
    const max = Math.max(1, ...trend);
    $("#dashTrend").innerHTML = (t.trend || []).map((x) =>
      `<div class="bar" style="height:${(x.count / max) * 100}%"><span class="v">${x.count}</span><span class="d">${x.date}</span></div>`
    ).join("");
  } catch (e) { $("#dashTrend").innerHTML = '<span class="muted">无数据</span>'; }

  // 类型分布
  try {
    const ty = await API.get("/api/stats/types");
    const types = ty.types || [];
    const total = types.reduce((a, b) => a + b.value, 0) || 1;
    $("#dashTypes").innerHTML = `
      <div style="width:100%">
        ${types.map((x) => `
          <div style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
              <span><span class="dot" style="display:inline-block;width:10px;height:10px;border-radius:3px;background:${x.color};margin-right:6px"></span>${escapeHtml(x.name)}</span>
              <span>${x.value}（${((x.value / total) * 100).toFixed(1)}%）</span>
            </div>
            <div style="height:8px;background:var(--border);border-radius:4px;overflow:hidden">
              <div style="height:100%;width:${(x.value / total) * 100}%;background:${x.color};border-radius:4px"></div>
            </div>
          </div>`).join("")}
      </div>`;
  } catch (e) { $("#dashTypes").innerHTML = '<span class="muted">无数据</span>'; }
}

/* ---------- 资源管理 ---------- */
let resOffset = 0, resTotal = 0;
async function loadResources() {
  const search = $("#resSearch").value.trim();
  const rtype = $("#resType").value;
  const status = $("#resStatus").value;
  let url = `/api/resources?limit=50&offset=${resOffset}`;
  if (search) url += "&search=" + encodeURIComponent(search);
  if (rtype) url += "&resource_type=" + rtype;
  if (status) url += "&status=" + status;
  try {
    const d = await API.get(url);
    resTotal = d.total || 0;
    $("#resTotal").textContent = `共 ${resTotal} 条`;
    $("#resPage").textContent = `${resOffset + 1}-${Math.min(resOffset + 50, resTotal)}`;
    $("#resBody").innerHTML = (d.resources || []).map((r) => `
      <tr>
        <td>${r.id}</td>
        <td style="max-width:340px;overflow:hidden;text-overflow:ellipsis" title="${escapeHtml(r.title)}">${escapeHtml(r.title)}</td>
        <td><span class="tag ${escapeHtml(r.resource_type)}">${r.resource_type === "game" ? "游戏" : "软件"}</span></td>
        <td><span class="tag ${escapeHtml(r.status)}">${escapeHtml(r.status)}</span></td>
        <td>${escapeHtml(r.source_site || "-")}</td>
        <td>${fmtSize(r.file_size)}</td>
        <td>${fmtTime(r.created_at)}</td>
        <td>
          <button class="btn btn-sm" onclick="viewResource(${r.id})">详情</button>
          <button class="btn btn-sm btn-danger" onclick="deleteResource(${r.id}, '${escapeHtml(r.title.replace(/'/g, "\\'"))}')">删除</button>
        </td>
      </tr>`).join("") || '<tr><td colspan="8" class="muted center">暂无资源</td></tr>';
  } catch (e) { toast("资源加载失败: " + e.message, true); }
}
async function viewResource(id) {
  try {
    const r = await API.get("/api/resources/" + id);
    const fields = ["id", "title", "resource_type", "status", "source_site", "source_url",
      "version", "platform", "language", "file_size", "category", "tags", "intro", "created_at"];
    const html = fields.map((f) =>
      `<div style="margin-bottom:8px"><b>${f}:</b> <span style="white-space:pre-wrap">${escapeHtml(r[f] ?? "-")}</span></div>`
    ).join("");
    showModal("资源 #" + id + " 详情", html);
  } catch (e) { toast("加载详情失败: " + e.message, true); }
}
async function deleteResource(id, title) {
  if (!confirm(`确定删除资源「${title}」吗？`)) return;
  try {
    const r = await API.del("/api/resources/" + id);
    toast("🗑️ " + (r.message || "已删除"));
    loadResources();
  } catch (e) { toast("删除失败: " + e.message, true); }
}
$("#resSearch").addEventListener("input", debounce(() => { resOffset = 0; loadResources(); }, 400));
$("#resType").addEventListener("change", () => { resOffset = 0; loadResources(); });
$("#resStatus").addEventListener("change", () => { resOffset = 0; loadResources(); });
$("#resRefresh").addEventListener("click", loadResources);
$("#resPrev").addEventListener("click", () => { if (resOffset >= 50) { resOffset -= 50; loadResources(); } });
$("#resNext").addEventListener("click", () => { if (resOffset + 50 < resTotal) { resOffset += 50; loadResources(); } });
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

/* ---------- Modal ---------- */
function showModal(title, bodyHtml) {
  const old = $("#modal");
  if (old) old.remove();
  const div = document.createElement("div");
  div.id = "modal";
  div.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:1000";
  div.innerHTML = `<div style="background:var(--panel);border:1px solid var(--border);border-radius:12px;max-width:640px;width:92%;max-height:80vh;display:flex;flex-direction:column">
    <div style="padding:14px 18px;border-bottom:1px solid var(--border);font-weight:600">${escapeHtml(title)}</div>
    <div style="padding:16px 18px;overflow-y:auto;font-size:13px;line-height:1.5">${bodyHtml}</div>
    <div style="padding:12px 18px;border-top:1px solid var(--border);text-align:right">
      <button class="btn" onclick="this.closest('#modal').remove()">关闭</button>
    </div></div>`;
  div.addEventListener("click", (e) => { if (e.target === div) div.remove(); });
  document.body.appendChild(div);
}

/* ---------- 任务中心 ---------- */
async function loadTasks() {
  try {
    const d = await API.get("/api/tasks");
    const act = d.active || [];
    $("#taskActive").innerHTML = act.length
      ? act.map((t) => `<div class="task-item"><span><span class="spin"></span><span class="t">${escapeHtml(t.title || t.task_id || t.id)}</span></span>
          <span class="s">${escapeHtml(t.status || "")}</span>
          <button class="btn btn-sm btn-danger" onclick="cancelTask('${escapeHtml(String(t.id || t.task_id))}')">取消</button></div>`).join("")
      : '<span class="muted">暂无运行中任务</span>';

    const logs = await API.get("/api/tasks/logs?limit=50");
    $("#taskBody").innerHTML = (logs.logs || []).map((l) => `
      <tr>
        <td>${l.resource_id ?? "-"}</td>
        <td>${escapeHtml(l.task_type || "-")}</td>
        <td><span class="tag ${escapeHtml(l.status)}">${escapeHtml(l.status || "-")}</span></td>
        <td>${fmtTime(l.started_at)}</td>
        <td style="max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeHtml(l.message)}">${escapeHtml(l.message || "")}</td>
      </tr>`).join("") || '<tr><td colspan="5" class="muted center">暂无日志</td></tr>';
  } catch (e) { toast("任务加载失败: " + e.message, true); }
}
async function cancelTask(id) {
  if (!confirm("确定取消该任务？")) return;
  try { await API.post("/api/tasks/" + id + "/cancel"); toast("✅ 已取消"); loadTasks(); }
  catch (e) { toast("取消失败: " + e.message, true); }
}

/* ---------- AI 对话 ---------- */
let curSession = null;
async function loadSessions() {
  try {
    const d = await API.get("/api/chat/history");
    const sessions = d.sessions || [];
    $("#sessionList").innerHTML = sessions.map((s) => `
      <div class="session-item ${s.session_id === curSession ? "active" : ""}" onclick="selectSession('${s.session_id}')">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(s.title || s.session_id)}</span>
        <span class="del" title="删除会话" onclick="event.stopPropagation();deleteSession('${s.session_id}')">✕</span>
      </div>`).join("") || '<span class="muted">暂无会话</span>';
  } catch (e) { toast("会话加载失败: " + e.message, true); }
}
async function selectSession(sid) {
  curSession = sid;
  loadSessions();
  await loadChatHistory(sid);
}
async function loadChatHistory(sid) {
  if (!sid) { $("#chatMessages").innerHTML = '<div class="muted center">选择或新建一个会话开始对话</div>'; return; }
  try {
    const d = await API.get("/api/chat/history?session_id=" + encodeURIComponent(sid));
    const msgs = d.messages || [];
    $("#chatMessages").innerHTML = msgs.map((m) => `
      <div class="msg ${m.role === "user" ? "user" : "assistant"}">
        ${renderMarkdown(m.content || "")}
        ${m.model ? `<span class="meta">模型: ${escapeHtml(m.model)} · ${fmtTime(m.created_at)}</span>` : ""}
      </div>`).join("") || '<div class="muted center">空会话</div>';
    const box = $("#chatMessages"); box.scrollTop = box.scrollHeight;
  } catch (e) { toast("历史加载失败: " + e.message, true); }
}
async function newChat() {
  try {
    const d = await API.post("/api/chat/send", { message: "__new_session__" });
    if (d.session_id) { curSession = d.session_id; loadSessions(); $("#chatMessages").innerHTML = ""; }
    else { const r = await API.get("/api/chat/history"); const s = (r.sessions || [])[0]; curSession = s && s.session_id; loadSessions(); }
  } catch (e) {
    const r = await API.get("/api/chat/history");
    const s = (r.sessions || [])[0];
    curSession = s ? s.session_id : null;
    loadSessions();
  }
}
async function deleteSession(sid) {
  if (!confirm("删除该会话？")) return;
  try { await API.del("/api/chat/session/" + encodeURIComponent(sid)); if (curSession === sid) curSession = null; loadSessions(); $("#chatMessages").innerHTML = ""; }
  catch (e) { toast("删除失败: " + e.message, true); }
}
let chatSending = false;
async function sendChat() {
  const text = $("#chatInput").value.trim();
  if (!text || chatSending) return;
  if (!curSession) { toast("请先新建或选择会话", true); return; }
  chatSending = true;
  $("#chatSend").disabled = true;
  $("#chatAbort").disabled = false;
  $("#chatInput").value = "";
  appendMsg("user", text);
  const p = appendMsg("assistant", "⏳ AI 思考中…（流式输出即将开始）", "pending streaming");
  let acc = "";
  try {
    const headers = { "Content-Type": "application/json" };
    if (API.token) headers["Authorization"] = "Bearer " + API.token;
    const resp = await fetch("/api/chat/send/stream", {
      method: "POST",
      headers,
      body: JSON.stringify({ session_id: curSession, message: text }),
    });
    if (!resp.ok) {
      let msg = "HTTP " + resp.status;
      try { const j = await resp.json(); msg = j.detail || msg; } catch (e) {}
      throw new Error(msg);
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop();
      for (const part of parts) {
        const line = part.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        let ev;
        try { ev = JSON.parse(line.slice(5)); } catch (e) { continue; }
        if (ev.type === "text_chunk") {
          acc += ev.content || "";
          p.classList.remove("pending");
          p.innerHTML = renderMarkdown(acc) + '<span class="cursor">▍</span>';
          const box = $("#chatMessages"); box.scrollTop = box.scrollHeight;
        } else if (ev.type === "done") {
          acc = ev.result || acc;
        } else if (ev.type === "error") {
          throw new Error(ev.message || "AI 出错");
        } else if (ev.type === "session_id") {
          curSession = ev.session_id;
        }
      }
    }
    p.classList.remove("pending", "streaming");
    p.innerHTML = renderMarkdown(acc);
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = "✓ 流式完成";
    p.appendChild(meta);
  } catch (e) {
    if (acc) { p.innerHTML = renderMarkdown(acc); }
    else { p.textContent = "❌ " + e.message; }
    p.classList.add("error");
  } finally {
    chatSending = false;
    $("#chatSend").disabled = false;
    $("#chatAbort").disabled = true;
    const box = $("#chatMessages"); box.scrollTop = box.scrollHeight;
  }
}
function appendMsg(role, text, extra) {
  const box = $("#chatMessages");
  const div = document.createElement("div");
  div.className = "msg " + role + (extra ? " " + extra : "");
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}
async function abortChat() {
  if (!curSession) return;
  try { await API.post("/api/chat/abort/" + encodeURIComponent(curSession)); toast("⏹ 已发送中止信号"); }
  catch (e) { toast("中止失败: " + e.message, true); }
}
$("#chatSend").addEventListener("click", sendChat);
$("#chatAbort").addEventListener("click", abortChat);
$("#chatNew").addEventListener("click", newChat);
$("#chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

/* ---------- 源站管理 ---------- */
async function loadSources() {
  try {
    const d = await API.get("/api/sources");
    $("#sourceBody").innerHTML = (d.sources || []).map((s) => `
      <tr>
        <td title="${escapeHtml(s.url || "")}">${escapeHtml(s.name)}</td>
        <td><span class="tag ${escapeHtml(s.site_type)}">${s.site_type === "game" ? "游戏" : "软件"}</span></td>
        <td>${s.crawl_interval ? s.crawl_interval + "分" : "-"}</td>
        <td>${s.enabled ? "✅" : "❌"}</td>
        <td>
          <button class="btn btn-sm" onclick="crawlSource(${s.id}, '${escapeHtml(s.name.replace(/'/g, "\\'"))}')">立即爬取</button>
          <button class="btn btn-sm btn-danger" onclick="deleteSource(${s.id}, '${escapeHtml(s.name.replace(/'/g, "\\'"))}')">删除</button>
        </td>
      </tr>`).join("") || '<tr><td colspan="5" class="muted center">暂无源站</td></tr>';
  } catch (e) { toast("源站加载失败: " + e.message, true); }
}
$("#sourceForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const body = {
    name: f.name.value.trim(), url: f.url.value.trim(),
    site_type: f.site_type.value, crawl_interval: parseInt(f.crawl_interval.value) || 360,
    need_login: f.need_login.checked,
    login_url: f.login_url.value.trim() || null,
    login_username: f.login_username.value.trim() || null,
    login_password: f.login_password.value || null,
    notes: f.notes.value.trim() || null,
  };
  try {
    await API.post("/api/sources", body);
    toast("✅ 源站已添加");
    f.reset();
    loadSources();
  } catch (err) { toast("添加失败: " + err.message, true); }
});
async function crawlSource(id, name) {
  if (!confirm(`立即爬取「${name}」？`)) return;
  try { await API.post(`/api/sources/${id}/crawl`); toast("✅ 已触发爬取"); }
  catch (e) { toast("触发失败: " + e.message, true); }
}
async function deleteSource(id, name) {
  if (!confirm(`删除源站「${name}」？`)) return;
  try { await API.del("/api/sources/" + id); toast("🗑️ 已删除"); loadSources(); }
  catch (e) { toast("删除失败: " + e.message, true); }
}

/* ---------- 系统设置 ---------- */
async function loadSettings() {
  try {
    const d = await API.get("/api/settings");
    $("#settingsRaw").textContent = JSON.stringify(d.settings, null, 2);
  } catch (e) { $("#settingsRaw").textContent = "加载失败: " + e.message; }
  try {
    const s = await API.get("/api/settings/scheduler");
    const data = s.scheduler || s;
    $("#schedulerBox").innerHTML = `
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <label class="chk"><input type="checkbox" id="schedEnabled" ${data.enabled ? "checked" : ""}> 启用定时调度</label>
        <label class="chk">间隔(分钟)<input type="number" id="schedInterval" value="${data.interval || 360}" style="width:90px"></label>
        <button id="schedSave" class="btn btn-primary">保存</button>
      </div>
      <div class="muted" style="margin-top:8px">下次运行: ${fmtTime(data.next_run_at)}</div>`;
    $("#schedSave").addEventListener("click", async () => {
      try {
        await API.put("/api/settings/scheduler", {
          enabled: $("#schedEnabled").checked,
          interval: parseInt($("#schedInterval").value) || 360,
        });
        toast("✅ 调度配置已保存"); loadSettings();
      } catch (e) { toast("保存失败: " + e.message, true); }
    });
  } catch (e) {
    $("#schedulerBox").innerHTML = '<span class="muted">调度信息不可用: ' + escapeHtml(e.message) + "</span>";
  }
}
$("#btnRestart").addEventListener("click", async () => {
  if (!confirm("确定重启软件服务？当前连接会断开约 30~60 秒。")) return;
  try { await API.post("/api/settings/restart"); toast("🔄 重启指令已发送"); }
  catch (e) { toast("重启指令发送失败: " + e.message, true); }
});

/* ---------- 代码变更 ---------- */
async function loadCodeChanges() {
  try {
    const d = await API.get("/api/code/changes?limit=50");
    const list = d.changes || [];
    $("#codeList").innerHTML = list.map((c) => {
      const cls = c.status === "failed" ? "failed" : (c.status === "rolled_back" ? "pending" : "published");
      return `
      <div class="code-item">
        <div class="code-head" onclick="toggleDiff(this)">
          <span class="tag ${cls}">${escapeHtml(c.action || "change")}</span>
          <span class="code-path" title="${escapeHtml(c.path)}">${escapeHtml(c.path)}</span>
          <span class="code-sum">${escapeHtml(c.summary || "")}</span>
          <span class="muted" style="margin-left:auto">${escapeHtml(c.ts_full || c.ts || "")}</span>
        </div>
        <pre class="diff hidden">${escapeHtml(c.diff || "（无 diff）")}</pre>
      </div>`;
    }).join("") || '<span class="muted">暂无变更记录</span>';
  } catch (e) {
    $("#codeList").innerHTML = '<span class="muted">加载失败: ' + escapeHtml(e.message) + "</span>";
  }
}
function toggleDiff(head) {
  const pre = head.nextElementSibling;
  if (pre) pre.classList.toggle("hidden");
}
$("#codeRefresh").addEventListener("click", loadCodeChanges);

/* ---------- 终端 ---------- */
async function runTerminal() {
  const cmd = $("#termInput").value.trim();
  if (!cmd) return;
  const out = $("#termOutput");
  out.textContent += (out.textContent ? "\n" : "") + "$ " + cmd + "\n";
  $("#termRun").disabled = true;
  try {
    const r = await API.post("/api/terminal/execute", { command: cmd });
    out.textContent += (r.output || "") + (r.exit_code === 0 ? "" : "\n[退出码 " + r.exit_code + "]");
  } catch (e) {
    out.textContent += "❌ " + e.message;
  } finally {
    $("#termRun").disabled = false;
    $("#termInput").value = "";
    out.scrollTop = out.scrollHeight;
  }
}
$("#termRun").addEventListener("click", runTerminal);
$("#termInput").addEventListener("keydown", (e) => { if (e.key === "Enter") runTerminal(); });
$("#termClear").addEventListener("click", () => { $("#termOutput").textContent = "就绪。"; });

/* ---------- 系统日志 ---------- */
let logAutoRefresh = true, logTimer = null;
async function loadLogs() {
  try {
    const d = await API.get("/api/logs/recent?lines=300");
    $("#logFileInfo").textContent = d.file ? "📄 " + d.file : "";
    const out = $("#logOutput");
    const lines = d.lines || [];
    out.textContent = lines.length ? lines.join("\n") : "（暂无日志）";
    // 自动刷新时保持底部最新
    if (logAutoRefresh) out.scrollTop = out.scrollHeight;
  } catch (e) {
    $("#logOutput").textContent = "加载失败: " + e.message;
  }
}
$("#logRefresh").addEventListener("click", loadLogs);
$("#logAuto").addEventListener("click", () => {
  logAutoRefresh = !logAutoRefresh;
  $("#logAuto").textContent = logAutoRefresh ? "⏸ 暂停自动刷新" : "▶ 恢复自动刷新";
  if (logAutoRefresh) loadLogs();
});
function startLogPolling() {
  if (logTimer) clearInterval(logTimer);
  logTimer = setInterval(() => {
    if (currentView === "logs" && logAutoRefresh) loadLogs();
  }, 3000);
}

/* ---------- 对话左侧实时控制台 ---------- */
let consolePaused = false, consoleTimer = null, consoleBuf = [];

/* 控制台日志高亮：解析 loguru 格式行 / emoji 前缀，输出安全 HTML */
function stripAnsi(s) {
  return String(s).replace(/\x1B\[[0-9;]*[A-Za-z]/g, "");
}
const CONSOLE_EMOJI_CLASS = {
  "✅": "ok", "✔": "ok", "🎉": "ok",
  "❌": "err", "⛔": "err", "💥": "err",
  "⚠️": "warn", "⏸": "warn", "🔄": "warn", "🔁": "warn",
  "🚀": "info", "🔌": "info", "🤖": "info", "📚": "info",
  "📎": "info", "⏳": "info", "📦": "info", "🔍": "info", "📢": "info"
};
/* 消息级关键词高亮（与桌面版 16 条高亮规则对齐，基于已转义文本，安全） */
function highlightMsgText(escaped) {
  const rules = [
    [/(💬\s*Agent:)/g, "cl-agent"],
    [/(👤\s*User:)/g, "cl-user"],
    [/\b(ERROR|CRITICAL|FATAL)\b/g, "cl-kw-err"],
    [/\b(WARNING|WARN)\b/g, "cl-kw-warn"],
    [/\b(SUCCESS|OK)\b/g, "cl-kw-ok"],
    [/\b(INFO|DEBUG)\b/g, "cl-kw-info"],
    [/\bhttps?:\/\/\S+/g, "cl-url"],
    [/\b[A-Za-z_][\w.]*\.py\b/g, "cl-file"],
    [/\b(\d+(?:\.\d+)?)\s*(GB|MB|KB|秒|s|ms|行|条)\b/g, "cl-num"],
    [/\b(True|False|None)\b/g, "cl-bool"],
  ];
  let out = escaped;
  for (const [re, cls] of rules) {
    out = out.replace(re, `<span class="${cls}">$&</span>`);
  }
  return out;
}
function highlightLogLine(raw) {
  const s = stripAnsi(raw == null ? "" : raw);
  if (!s || !s.trim()) return "";
  // 前端保底过滤：uvicorn HTTP 访问日志（轮询/健康检查等）不进实时控制台
  if ((s.includes('GET ') || s.includes('POST ') || s.includes('PUT ')) &&
      s.includes('HTTP/1.1') && s.includes('/api/')) return "";
  // 标准 loguru 格式: 时间 | 级别 | 模块 | 消息（时间精简为 HH:MM:SS，更接近桌面版）
  const m = s.match(/^(\d{4}-\d{2}-\d{2}[ T][\d:.]+)\s*\|\s*(DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)\s*\|\s*(.*)$/);
  if (m) {
    let time = m[1];
    const tm = time.match(/\d{2}:\d{2}:\d{2}/);
    if (tm) time = tm[0];
    const lv = m[2].toLowerCase();
    const rest = m[3];
    const pipe = rest.indexOf("|");
    let mod = "", msg = rest;
    if (pipe >= 0) { mod = escapeHtml(rest.slice(0, pipe).trim()); msg = rest.slice(pipe + 1); }
    return `<span class="cl-time">${escapeHtml(time)}</span> <span class="cl-level lv-${lv}">${m[2]}</span>` +
      (mod ? ` <span class="cl-module">${mod}</span>` : "") +
      ` <span class="cl-msg">${highlightMsgText(escapeHtml(msg))}</span>`;
  }
  // 简单行：emoji 前缀决定整行颜色 + 关键词高亮
  const first = s.trim().slice(0, 2);
  const cls = CONSOLE_EMOJI_CLASS[first];
  return `<span class="cl-plain${cls ? " cl-" + cls : ""}">${highlightMsgText(escapeHtml(s))}</span>`;
}
function renderConsole() {
  const out = $("#consoleOutput");
  if (!out) return;
  out.innerHTML = consoleBuf.length
    ? consoleBuf.join("\n")
    : '<span class="cl-empty">（暂无日志）</span>';
  out.scrollTop = out.scrollHeight;
}
function appendConsole(text) {
  if (!text) return;
  const out = $("#consoleOutput");
  if (!out || consolePaused) return;
  const MAX = 500;
  String(text).split("\n").forEach((l) => {
    const html = highlightLogLine(l);
    if (html) consoleBuf.push(html);
  });
  if (consoleBuf.length > MAX) consoleBuf = consoleBuf.slice(-MAX);
  renderConsole();
}
async function loadChatConsole() {
  const out = $("#consoleOutput");
  if (consolePaused) return;
  try {
    const d = await API.get("/api/logs/recent?lines=150&source=ring");
    const lines = d.lines || [];
    consoleBuf = lines.map(highlightLogLine).filter(Boolean);
    if (consoleBuf.length > 500) consoleBuf = consoleBuf.slice(-500);
    renderConsole();
  } catch (e) {
    out.innerHTML = '<span class="cl-err">控制台加载失败: ' + escapeHtml(e.message) + "</span>";
  }
}
$("#consolePause").addEventListener("click", () => {
  consolePaused = !consolePaused;
  $("#consolePause").textContent = consolePaused ? "▶" : "⏸";
  $("#consoleOutput").classList.toggle("paused", consolePaused);
  if (!consolePaused) loadChatConsole();
});
$("#consoleClear").addEventListener("click", () => { $("#consoleOutput").textContent = ""; });
function startConsolePolling() {
  if (consoleTimer) clearInterval(consoleTimer);
  consoleTimer = setInterval(() => { if (currentView === "chat") loadChatConsole(); }, 3000);
}

/* 控制台/对话 分隔条拖拽（自由调整左右宽度，默认 50/50） */
(function initChatResizer() {
  const resizer = document.querySelector(".chat-resizer");
  const layout = document.querySelector(".chat-layout");
  if (!resizer || !layout) return;
  let dragging = false;
  resizer.addEventListener("mousedown", (e) => {
    dragging = true;
    resizer.classList.add("active");
    document.body.style.userSelect = "none";
    e.preventDefault();
  });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    if (rect.width <= 0) return;
    let pct = ((e.clientX - rect.left) / rect.width) * 100;
    pct = Math.max(15, Math.min(85, pct));
    document.querySelector(".chat-console-pane").style.flex = `0 0 ${pct}%`;
  });
  document.addEventListener("mouseup", () => {
    if (dragging) {
      dragging = false;
      resizer.classList.remove("active");
      document.body.style.userSelect = "";
    }
  });
})();

/* ---------- 更新 ---------- */
let updateTaskId = null, updatePollTimer = null;
async function loadUpdate() {
  const box = $("#updateBox");
  try {
    const d = await API.get("/api/update/check");
    if (!d.has_update) {
      box.innerHTML = `<div class="ok-line">✅ 当前已是最新版本：<b>v${escapeHtml(d.current)}</b></div>`;
      return;
    }
    const info = d.latest || {};
    box.innerHTML = `
      <div style="margin-bottom:12px">当前版本：<b>v${escapeHtml(d.current)}</b></div>
      <div style="margin-bottom:16px">发现新版本：<b class="up-new">v${escapeHtml(info.version || info.tag || "?")}</b></div>
      <div class="muted" style="margin-bottom:16px;white-space:pre-wrap">${escapeHtml((info.notes || info.description || "").slice(0, 500))}</div>
      <button id="upDownload" class="btn btn-primary">⬇️ 下载更新</button>
      <button id="upApply" class="btn btn-danger" style="display:none">🔄 应用更新并重启</button>
      <div id="upProgress" class="muted" style="margin-top:12px"></div>`;
    $("#upDownload").addEventListener("click", startUpdate);
    $("#upApply").addEventListener("click", applyUpdate);
  } catch (e) {
    box.innerHTML = '<span class="muted">检查更新失败: ' + escapeHtml(e.message) + "</span>";
  }
}
async function startUpdate() {
  try {
    const d = await API.post("/api/update/download");
    updateTaskId = d.task_id;
    $("#upProgress").textContent = "⬇️ 下载中…";
    if (updatePollTimer) clearInterval(updatePollTimer);
    updatePollTimer = setInterval(pollUpdate, 2000);
  } catch (e) { $("#upProgress").textContent = "❌ " + e.message; }
}
async function pollUpdate() {
  if (!updateTaskId) return;
  try {
    const p = await API.get("/api/update/progress?task_id=" + updateTaskId);
    if (p.status === "done") {
      clearInterval(updatePollTimer); updatePollTimer = null;
      $("#upProgress").textContent = "✅ 下载完成";
      $("#upApply").style.display = "";
      $("#upDownload").style.display = "none";
    } else if (p.status === "error") {
      clearInterval(updatePollTimer); updatePollTimer = null;
      $("#upProgress").textContent = "❌ " + p.error;
    } else {
      $("#upProgress").textContent = `⬇️ 下载中… ${fmtSize(p.done)} / ${fmtSize(p.total || "?")}`;
    }
  } catch (e) {}
}
async function applyUpdate() {
  if (!confirm("确定应用更新？软件将自动重启，当前连接会断开。")) return;
  try { await API.post("/api/update/apply"); toast("🔄 正在应用更新…"); }
  catch (e) { toast("应用失败: " + e.message, true); }
}

/* ---------- 启动 ---------- */
$("#tokenInput").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#tokenBtn").click(); });
initSettingsTabs();
connectWS();
switchView("chat");
loadLicenseStatus();
startLogPolling();
startConsolePolling();
// 代码变更轮询：仅当停留在 code 视图时每 10s 自动刷新
setInterval(() => { if (currentView === "code") loadCodeChanges(); }, 10000);


/* ========== 系统设置 9 Tab（与桌面版对齐） ========== */
let aiConfigsCache = null, aiActiveKey = "";
function initSettingsTabs() {
  $$(".stab").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".stab").forEach((b) => b.classList.toggle("active", b === btn));
      $$(".stab-panel").forEach((p) => p.classList.add("hidden"));
      const panel = $("#stab-" + btn.dataset.stab);
      if (panel) panel.classList.remove("hidden");
    });
  });
  $("#aiConfigList").addEventListener("change", (e) => selectAiConfig(e.target.value));
  $("#aiAdd").addEventListener("click", addAiConfig);
  $("#aiDel").addEventListener("click", deleteAiConfig);
  $("#aiActivate").addEventListener("click", activateAiConfig);
  $("#aiSave").addEventListener("click", saveAiConfig);
  $("#visSave").addEventListener("click", saveVisionConfig);
  $("#siteSave").addEventListener("click", saveSiteSettings);
  $("#ossSave").addEventListener("click", saveOssSettings);
  $("#pluginRefresh").addEventListener("click", loadPlugins);
  $("#marketPluginRefresh").addEventListener("click", loadMarketPlugins);
  $("#swScan").addEventListener("click", scanSoftware);
  $("#memRefresh").addEventListener("click", loadMemories);
  $("#memKeyword").addEventListener("keydown", (e) => { if (e.key === "Enter") loadMemories(); });
  $("#memSection").addEventListener("change", loadMemories);
  $("#promptType").addEventListener("change", loadPrompt);
  $("#promptRefresh").addEventListener("click", loadPrompt);
  $("#aboutCheckUpdate").addEventListener("click", loadAboutUpdate);
}

/* 进入设置页时加载全部 tab 数据 */
const _origLoadSettings = loadSettings;
loadSettings = function () {
  _origLoadSettings();
  loadSettingsTabs();
};
function loadSettingsTabs() {
  loadAiSettings();
  loadSiteSettings();
  loadOssSettings();
  loadPlugins();
  loadCapabilities();
  loadSoftware();
  loadMemories();
  loadPrompt();
  loadAbout();
}

/* --- AI 模型 --- */
async function loadAiSettings() {
  try {
    const d = await API.get("/api/settings");
    const ai = d.settings.ai || {};
    aiConfigsCache = ai.configs || {};
    aiActiveKey = ai.active || "";
    const keys = Object.keys(aiConfigsCache);
    $("#aiConfigList").innerHTML = keys.map((k) => `<option value="${escapeHtml(k)}">${escapeHtml(k)}${k === aiActiveKey ? " ⭐" : ""}</option>`).join("");
    $("#aiActiveLabel").textContent = aiActiveKey ? `（当前启用: ${escapeHtml(aiActiveKey)}）` : "";
    const vis = ai.vision || {};
    $("#visKey").value = vis.api_key || "";
    $("#visBase").value = vis.base_url || "https://open.bigmodel.cn/api/paas/v4";
    $("#visModel").value = vis.model || "glm-4v-flash";
    if (keys.length) selectAiConfig(keys[0]);
  } catch (e) { toast("AI 配置加载失败: " + e.message, true); }
}
function selectAiConfig(key) {
  const cfg = (aiConfigsCache || {})[key];
  if (!cfg) return;
  $("#aiName").value = key;
  $("#aiProvider").value = cfg.provider || "deepseek";
  $("#aiModel").value = cfg.model || "";
  $("#aiKey").value = cfg.api_key || "";
  $("#aiBase").value = cfg.base_url || "";
}
function addAiConfig() {
  const key = ($("#aiName").value || "").trim();
  if (!key) { toast("请先填写配置名称", true); return; }
  if (!aiConfigsCache) aiConfigsCache = {};
  aiConfigsCache[key] = { provider: "deepseek", model: "", api_key: "", base_url: "https://api.deepseek.com/v1" };
  refreshAiList(key);
  toast("已新建配置 " + key + "，填写后点保存");
}
function deleteAiConfig() {
  const key = $("#aiConfigList").value;
  if (!key) return;
  if (!confirm(`确定删除 AI 配置「${key}」？`)) return;
  delete aiConfigsCache[key];
  refreshAiList(Object.keys(aiConfigsCache)[0] || "");
  toast("已标记删除，点「保存模型配置」生效");
}
function activateAiConfig() {
  const key = $("#aiConfigList").value;
  if (!key) return;
  aiActiveKey = key;
  refreshAiList(key);
  toast("已切换启用 " + key + "，点「保存模型配置」生效");
}
function refreshAiList(selectKey) {
  $("#aiConfigList").innerHTML = Object.keys(aiConfigsCache).map((k) => `<option value="${escapeHtml(k)}">${escapeHtml(k)}${k === aiActiveKey ? " ⭐" : ""}</option>`).join("");
  if (selectKey) { $("#aiConfigList").value = selectKey; selectAiConfig(selectKey); }
  $("#aiActiveLabel").textContent = aiActiveKey ? `（当前启用: ${escapeHtml(aiActiveKey)}）` : "";
}
async function saveAiConfig() {
  const key = ($("#aiName").value || "").trim();
  if (!key) { toast("请填写配置名称", true); return; }
  const cfg = {
    provider: $("#aiProvider").value,
    model: ($("#aiModel").value || "").trim(),
    api_key: ($("#aiKey").value || "").trim(),
    base_url: ($("#aiBase").value || "").trim(),
  };
  if (!aiConfigsCache) aiConfigsCache = {};
  aiConfigsCache[key] = cfg;
  try {
    await API.put("/api/settings", { ai: { active: aiActiveKey || key, configs: { [key]: cfg } } });
    toast("✅ 模型配置已保存");
    loadAiSettings();
  } catch (e) { toast("保存失败: " + e.message, true); }
}
async function saveVisionConfig() {
  const vis = {
    api_key: ($("#visKey").value || "").trim(),
    base_url: ($("#visBase").value || "").trim(),
    model: ($("#visModel").value || "").trim(),
  };
  try {
    await API.put("/api/settings", { ai: { vision: vis } });
    toast("✅ 视觉模型已保存");
  } catch (e) { toast("保存失败: " + e.message, true); }
}

/* --- 站点设置 --- */
async function loadSiteSettings() {
  try {
    const d = await API.get("/api/settings");
    const s = d.settings.site_7tan || {};
    $("#siteUrl").value = s.base_url || "";
    $("#siteUser").value = s.username || "";
    $("#sitePass").value = (s.password && s.password.includes("•")) ? "" : (s.password || "");
  } catch (e) {}
}
async function saveSiteSettings() {
  const payload = { site_7tan: {} };
  const url = ($("#siteUrl").value || "").trim();
  const user = ($("#siteUser").value || "").trim();
  const pass = $("#sitePass").value;
  if (url) payload.site_7tan.base_url = url;
  if (user) payload.site_7tan.username = user;
  if (pass && !pass.includes("•")) payload.site_7tan.password = pass;
  try {
    await API.put("/api/settings", payload);
    toast("✅ 站点设置已保存");
    loadSiteSettings();
  } catch (e) { toast("保存失败: " + e.message, true); }
}

/* --- OSS 存储 --- */
async function loadOssSettings() {
  try {
    const d = await API.get("/api/settings");
    const o = d.settings.oss || {};
    $("#ossBucket").value = o.bucket || "";
    $("#ossEndpoint").value = o.endpoint || "";
    $("#ossKey").value = o.access_key || "";
    $("#ossSecret").value = (o.secret_key && o.secret_key.includes("•")) ? "" : (o.secret_key || "");
  } catch (e) {}
}
async function saveOssSettings() {
  const payload = { oss: {} };
  const bucket = ($("#ossBucket").value || "").trim();
  const endpoint = ($("#ossEndpoint").value || "").trim();
  const key = ($("#ossKey").value || "").trim();
  const secret = $("#ossSecret").value;
  if (bucket) payload.oss.bucket = bucket;
  if (endpoint) payload.oss.endpoint = endpoint;
  if (key) payload.oss.access_key = key;
  if (secret && !secret.includes("•")) payload.oss.secret_key = secret;
  try {
    await API.put("/api/settings", payload);
    toast("✅ OSS 配置已保存");
    loadOssSettings();
  } catch (e) { toast("保存失败: " + e.message, true); }
}

/* --- 插件市场（设置页入口） --- */
async function loadPlugins() {
  const list = $("#pluginList");
  try {
    const d = await API.get("/api/settings/plugins");
    $("#pluginStats").textContent = `（已安装 ${d.installed_count} / 共 ${d.total}）`;
    list.innerHTML = (d.plugins || []).map((p) => `
      <div class="plugin-card">
        <h4>${escapeHtml(p.icon || "🧩")} ${escapeHtml(p.name)} <span class="badge ${p.installed ? "installed" : ""}">${p.installed ? "已安装" : "未安装"}</span></h4>
        <div class="plugin-desc">${escapeHtml(p.description || "")}</div>
        <div class="plugin-tools">工具: ${escapeHtml((p.tools || []).join(", ") || "-")} ｜ 版本 ${escapeHtml(p.version || "-")} ｜ ${escapeHtml(p.author || "")}</div>
        <div class="plugin-actions">
          ${p.installed
            ? `<button class="btn btn-sm btn-danger" onclick="uninstallPlugin('${p.id}')">🗑️ 卸载</button>`
            : `<button class="btn btn-sm btn-primary" onclick="installPlugin('${p.id}')">📥 安装</button>`}
        </div>
      </div>`).join("") || '<span class="muted">无可用插件</span>';
  } catch (e) { list.innerHTML = '<span class="muted">加载失败: ' + escapeHtml(e.message) + "</span>"; }
}
async function installPlugin(id) {
  try { await API.post(`/api/settings/plugins/${encodeURIComponent(id)}/install`); toast("✅ " + id + " 安装成功（重启后生效）"); loadPlugins(); loadMarketPlugins(); }
  catch (e) { toast("安装失败: " + e.message, true); }
}
async function uninstallPlugin(id) {
  if (!confirm(`确定卸载插件「${id}」？`)) return;
  try { await API.post(`/api/settings/plugins/${encodeURIComponent(id)}/uninstall`); toast("🗑️ " + id + " 已卸载"); loadPlugins(); loadMarketPlugins(); }
  catch (e) { toast("卸载失败: " + e.message, true); }
}

/* --- 插件市场（左侧栏独立页面入口） --- */
async function loadMarketPlugins() {
  const list = $("#marketPluginList");
  if (!list) return;
  try {
    const d = await API.get("/api/settings/plugins");
    const statsEl = $("#marketPluginStats");
    if (statsEl) statsEl.textContent = `（已安装 ${d.installed_count} / 共 ${d.total}）`;
    list.innerHTML = (d.plugins || []).map((p) => `
      <div class="plugin-card">
        <h4>${escapeHtml(p.icon || "🧩")} ${escapeHtml(p.name)} <span class="badge ${p.installed ? "installed" : ""}">${p.installed ? "已安装" : "未安装"}</span></h4>
        <div class="plugin-desc">${escapeHtml(p.description || "")}</div>
        <div class="plugin-tools">工具: ${escapeHtml((p.tools || []).join(", ") || "-")} ｜ 版本 ${escapeHtml(p.version || "-")} ｜ ${escapeHtml(p.author || "")}</div>
        <div class="plugin-actions">
          ${p.installed
            ? `<button class="btn btn-sm btn-danger" onclick="uninstallPlugin('${p.id}')">🗑️ 卸载</button>`
            : `<button class="btn btn-sm btn-primary" onclick="installPlugin('${p.id}')">📥 安装</button>`}
        </div>
      </div>`).join("") || '<span class="muted">无可用插件</span>';
  } catch (e) { list.innerHTML = '<span class="muted">加载失败: ' + escapeHtml(e.message) + "</span>"; }
}

/* --- 能力清单 --- */
async function loadCapabilities() {
  const el = $("#capList");
  try {
    const d = await API.get("/api/settings/capabilities");
    const st = d.stats || {};
    $("#capStats").textContent = `（分类 ${st.categories} · 工具 ${st.total} · 本地 ${st.local} · 云 ${st.cloud}）`;
    el.innerHTML = (d.groups || []).map((g) => `
      <div class="cap-group">
        <h4>${escapeHtml(g.icon || "📦")} ${escapeHtml(g.category || "")}</h4>
        ${(g.items || []).map((it) => `<div class="cap-item"><b>${escapeHtml(it.name || "")}</b> — ${escapeHtml(it.desc || "")} <span class="cap-tool">[${escapeHtml(it.tool || "")}]</span></div>`).join("")}
      </div>`).join("") || '<span class="muted">暂无能力数据</span>';
  } catch (e) { el.innerHTML = '<span class="muted">加载失败: ' + escapeHtml(e.message) + "</span>"; }
}

/* --- 环境引擎 --- */
async function loadSoftware() {
  const body = $("#swBody");
  try {
    const d = await API.get("/api/settings/software");
    body.innerHTML = (d.software || []).map((s) => `
      <tr>
        <td>${escapeHtml(s.category || "")}</td>
        <td>${escapeHtml(s.icon || "")} ${escapeHtml(s.name || "")}</td>
        <td>${escapeHtml(s.version || "")}</td>
        <td title="${escapeHtml(s.install_path || "")}">${escapeHtml(s.install_path || "")}</td>
        <td>${s.is_working ? "✅" : "❌"}</td>
      </tr>`).join("") || '<tr><td colspan="5" class="muted">暂无数据</td></tr>';
  } catch (e) { body.innerHTML = '<tr><td colspan="5" class="muted">加载失败: ' + escapeHtml(e.message) + "</td></tr>"; }
}
async function scanSoftware() {
  try {
    toast("🔄 正在扫描…");
    await API.post("/api/settings/software/scan");
    toast("✅ 扫描完成");
    loadSoftware();
  } catch (e) { toast("扫描失败: " + e.message, true); }
}

/* --- 记忆系统 --- */
async function loadMemories() {
  const el = $("#memList");
  const section = $("#memSection").value;
  const keyword = ($("#memKeyword").value || "").trim();
  try {
    const qs = new URLSearchParams();
    if (section) qs.set("section", section);
    if (keyword) qs.set("keyword", keyword);
    const d = await API.get("/api/settings/memories?" + qs.toString());
    $("#memTotal").textContent = `共 ${d.total} 条`;
    el.innerHTML = (d.memories || []).map((m) => `
      <div class="mem-item">
        <div class="mem-head">
          <span class="mem-section">${escapeHtml(m.section || "")}</span>
          <span class="mem-key">${escapeHtml(m.key || "")}</span>
          <span class="muted" style="margin-left:auto;font-size:11px">${escapeHtml(m.updated_at || m.created_at || "")}</span>
        </div>
        <div class="mem-content">${escapeHtml(m.content || "")}</div>
        <div class="mem-actions">
          <button class="btn btn-sm btn-danger" onclick="deleteMemoryItem('${escapeHtml(m.section || "")}','${escapeHtml(m.key || "")}')">🗑 删除</button>
        </div>
      </div>`).join("") || '<span class="muted">暂无记忆</span>';
  } catch (e) { el.innerHTML = '<span class="muted">加载失败: ' + escapeHtml(e.message) + "</span>"; }
}
async function deleteMemoryItem(section, key) {
  if (!confirm(`确定删除记忆「${section}/${key}」？`)) return;
  try {
    await API.del(`/api/settings/memories?section=${encodeURIComponent(section)}&key=${encodeURIComponent(key)}`);
    toast("🗑️ 已删除");
    loadMemories();
  } catch (e) { toast("删除失败: " + e.message, true); }
}

/* --- 系统提示词 --- */
async function loadPrompt() {
  const type = $("#promptType").value || "system";
  try {
    const d = await API.get("/api/settings/prompt?prompt_type=" + encodeURIComponent(type));
    const p = d.prompt || {};
    $("#promptContent").textContent = p.content || "（无内容）";
    $("#promptMeta").textContent = (p.char_count != null) ? `（${p.char_count} 字 / ${p.line_count} 行）` : "";
  } catch (e) { $("#promptContent").textContent = "加载失败: " + e.message; }
}

/* --- 关于 --- */
async function loadAbout() {
  try {
    const d = await API.get("/api/settings/about");
    const i = d.info || {};
    const verTxt = "v" + (i.version || "-") + (i.build_id && !String(i.build_id).startsWith("FREE") ? " · " + escapeHtml(i.build_id) : "");
    const fields = [
      ["版本", "v" + (i.version || "-")],
      ["构建", i.build_id || "-"],
      ["项目根目录", i.project_root || "-"],
      ["日志目录", i.log_dir || "-"],
      ["插件目录", i.plugin_dir || "-"],
      ["站点", i.site_root || "-"],
    ];
    const introText = [
      "7Tan AI工具 是一款由 AI 驱动的个人创作与开发助手，代号「盘古」。",
      "它将软件研发、游戏内容生产、系统运维三大能力融为一体，",
      "让 AI 不只是聊天，而是真正替你干活。",
      "",
      "【核心能力】",
      "🤖 AI 智能中枢 — 接入 DeepSeek 等大模型，支持深度推理、代码生成、文案创作与多轮对话",
      "",
      "🌐 游戏内容工厂 — 自动采集游戏资讯、撰写评测简介、配图处理、敏感词审核，一键发布到网站",
      "",
      "💻 全栈开发助手 — 代码检索/审查/测试/重构、Git 版本管理、Docker/K8s 运维、ADB 设备调试，200+ 工具随叫随到",
      "",
      "🧠 自我进化系统 — 可自主创建插件、优化提示词、管理记忆，越用越聪明",
      "",
      "🎬 录屏与制图 — 屏幕录制、图像生成、语音合成",
      "",
      "【出品】7Tan 团队",
    ].join("\n");
    document.getElementById("aboutInfo").innerHTML = [
      "<div style='text-align:center;padding:8px 0 2px'>",
      "<img src='/logo/logo_v4_256.png' alt='7Tan AI工具' style='width:96px;height:96px;border-radius:18px;object-fit:contain;background:#16213e;padding:8px' onerror=\"this.style.display='none'\">",
      "<div style='font-size:22px;font-weight:bold;margin-top:10px'>7Tan AI工具</div>",
      "<div style='font-size:13px;opacity:.65;margin-top:2px'>" + verTxt + "</div>",
      "</div>",
      "<div style='margin-top:14px;line-height:1.9;font-size:13px;white-space:pre-wrap'>" + escapeHtml(introText) + "</div>",
      "<details style='margin-top:14px'><summary style='cursor:pointer;opacity:.7;font-size:12px'>📋 技术信息</summary>",
      "<div class='form' style='margin-top:8px'>" + fields.map(function(f){ return "<label>" + escapeHtml(f[0]) + "<input value=\"" + escapeHtml(f[1]) + "\" readonly style=\"background:#0b0d12\"></label>"; }).join("") + "</div>",
      "</details>",
    ].join("");
  } catch (e) { document.getElementById("aboutInfo").textContent = "加载失败: " + e.message; }
}
async function loadAboutUpdate() {
  const msg = $("#aboutUpdateMsg");
  msg.textContent = "检查中…";
  try {
    const d = await API.get("/api/update/check");
    msg.textContent = d.has_update ? `发现新版本 v${escapeHtml((d.latest || {}).version || "")}` : `✅ 已是最新版本 v${escapeHtml(d.current)}`;
  } catch (e) { msg.textContent = "检查失败: " + e.message; }
}


/* ---------- 代码编辑（文件浏览器 + 在线编辑器，类 Harness 工作区） ---------- */
let edCurrent = null;            // 当前打开文件 {path, mtime}
let edDirty = false;             // 是否有未保存修改
const edOpenDirs = new Set();    // 已展开的目录（相对路径）

function edIcon(t, name) {
  if (t === "dir") return "📁";
  const m = /\.([^.]+)$/.exec(name);
  const ext = m ? m[1].toLowerCase() : "";
  const icons = { py:"🐍", js:"🟨", ts:"🟦", jsx:"⚛️", tsx:"⚛️", html:"🌐", css:"🎨", scss:"🎨",
    json:"📋", md:"📄", txt:"📄", yaml:"⚙️", yml:"⚙️", toml:"⚙️", ini:"⚙️", cfg:"⚙️",
    sql:"🗄️", sh:"🐚", bat:"🖥️", cmd:"🖥️", ps1:"🖥️", xml:"📰", vue:"💚",
    go:"🐹", rs:"🦀", java:"☕", kt:"🟣", c:"©️", cpp:"➕", h:"📑", cs:"#️⃣",
    gitignore:"🚫", lock:"🔒", env:"🔑", example:"🧪" };
  return icons[ext] || "📄";
}

async function edList(dir) {
  const d = await API.get("/api/files/tree?dir=" + encodeURIComponent(dir || ""));
  if (d.error) throw new Error(d.error);
  return d.entries || [];
}

/* 递归构建文件树（懒加载：只加载展开的目录） */
async function edBuildNode(dir, depth) {
  const wrap = document.createElement("div");
  let entries;
  try {
    entries = await edList(dir);
  } catch (e) {
    const err = document.createElement("div");
    err.className = "muted";
    err.style.padding = "6px 8px";
    err.textContent = e.message;
    wrap.appendChild(err);
    return wrap;
  }
  for (const it of entries) {
    const row = document.createElement("div");
    const isDir = it.type === "dir";
    const open = edOpenDirs.has(it.path);
    row.className = "tree-item " + (isDir ? "dir" : "file");
    if (isDir && it.hidden) row.classList.add("hidden-item");
    row.style.paddingLeft = (8 + depth * 14) + "px";
    row.title = it.path + (isDir && it.hidden ? "（受保护目录，不可展开）" : "");
    const caret = isDir ? (open ? "▾ " : "▸ ") : "";
    row.innerHTML = '<span class="tw">' + caret + edIcon(it.type, it.name) + '</span>' +
      '<span class="tn">' + escapeHtml(it.name) + "</span>" +
      (!isDir && it.size > 0 ? '<span class="ts muted">' + fmtSize(it.size) + "</span>" : "");
    if (isDir) {
      row.addEventListener("click", () => {
        if (it.hidden) { toast("该目录受保护（node_modules / .git / .venv 等），不可展开", true); return; }
        if (edOpenDirs.has(it.path)) edOpenDirs.delete(it.path); else edOpenDirs.add(it.path);
        edRender();
      });
      wrap.appendChild(row);
      if (open) wrap.appendChild(await edBuildNode(it.path, depth + 1));
    } else {
      row.addEventListener("click", () => edOpenFile(it.path));
      if (edCurrent && edCurrent.path === it.path) row.classList.add("active");
      wrap.appendChild(row);
    }
  }
  return wrap;
}

async function edRender() {
  const box = $("#edTree");
  if (!box) return;
  box.innerHTML = '<div class="muted" style="padding:8px">加载中…</div>';
  try {
    const root = await edBuildNode("", 0);
    box.innerHTML = "";
    box.appendChild(root);
    const d = await API.get("/api/files/tree?dir=");
    const r = $("#edRoot");
    if (r && d && d.root) r.textContent = "项目根: /" + (d.root === "." ? "" : d.root);
  } catch (e) {
    box.innerHTML = '<span class="muted">' + escapeHtml(e.message) + "</span>";
  }
}

/* 打开文件 */
async function edOpenFile(path) {
  if (edDirty && !confirm("当前文件有未保存的修改，确定放弃并打开其他文件？")) return;
  try {
    const d = await API.get("/api/files/read?path=" + encodeURIComponent(path));
    if (d.error) { toast("❌ " + d.error, true); return; }
    edCurrent = { path: d.path, mtime: d.mtime };
    edDirty = false;
    $("#edPath").value = d.path;
    $("#edContent").value = d.content;
    $("#edMeta").textContent = fmtSize(d.size) + " · " + fmtTime(new Date(d.mtime * 1000).toISOString());
    $("#edStatus").textContent = "已打开";
    edRenderGutter();
    edRender();
  } catch (e) {
    toast("❌ 打开失败: " + e.message, true);
  }
}

/* 行号 */
function edRenderGutter() {
  const ta = $("#edContent");
  const g = $("#edGutter");
  const n = Math.min(ta.value.split("\n").length, 5000);
  let html = "";
  for (let i = 1; i <= n; i++) html += i + "\n";
  g.textContent = html;
  g.scrollTop = ta.scrollTop;
}

/* 保存 */
async function edSave() {
  if (!edCurrent) return;
  const btn = $("#edSave");
  btn.disabled = true;
  try {
    const r = await API.post("/api/files/write", { path: edCurrent.path, content: $("#edContent").value });
    if (r.error) { toast("❌ " + r.error, true); return; }
    edDirty = false;
    $("#edStatus").textContent = "已保存 " + new Date().toLocaleTimeString();
    toast("✅ 已保存: " + edCurrent.path);
    edRender();
  } catch (e) {
    toast("❌ 保存失败: " + e.message, true);
  } finally {
    btn.disabled = false;
  }
}

/* 新建文件/目录 */
async function edCreate(type) {
  const label = type === "dir" ? "文件夹名" : "文件名";
  const name = prompt("请输入要新建的" + label + "：", type === "dir" ? "new_dir" : "new_file.py");
  if (!name) return;
  let base = "";
  if (edCurrent && edCurrent.path.includes("/")) base = edCurrent.path.slice(0, edCurrent.path.lastIndexOf("/"));
  const path = base ? base + "/" + name : name;
  try {
    const r = await API.post("/api/files/create", { path, type });
    if (r.error) { toast("❌ " + r.error, true); return; }
    toast("✅ 已创建 " + name);
    if (base) edOpenDirs.add(base);
    await edRender();
    if (type === "file") edOpenFile(r.path);
  } catch (e) {
    toast("❌ 创建失败: " + e.message, true);
  }
}

/* 删除当前文件 */
async function edDelete() {
  if (!edCurrent) return;
  if (!confirm("确定删除文件？\n" + edCurrent.path + "\n（删除后不可恢复）")) return;
  try {
    const r = await API.del("/api/files/delete?path=" + encodeURIComponent(edCurrent.path));
    if (r.error) { toast("❌ " + r.error, true); return; }
    toast("🗑️ 已删除: " + edCurrent.path);
    edCurrent = null; edDirty = false;
    $("#edContent").value = "";
    $("#edPath").value = "";
    $("#edMeta").textContent = "";
    $("#edStatus").textContent = "未打开文件";
    edRenderGutter();
    edRender();
  } catch (e) {
    toast("❌ 删除失败: " + e.message, true);
  }
}

/* 事件绑定 */
$("#edRefresh").addEventListener("click", edRender);
$("#edNewFile").addEventListener("click", () => edCreate("file"));
$("#edNewDir").addEventListener("click", () => edCreate("dir"));
$("#edSave").addEventListener("click", edSave);
$("#edDelete").addEventListener("click", edDelete);
$("#edContent").addEventListener("input", () => {
  edDirty = true;
  $("#edStatus").textContent = "未保存";
  edRenderGutter();
});
$("#edContent").addEventListener("scroll", () => {
  $("#edGutter").scrollTop = $("#edContent").scrollTop;
});
$("#edContent").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
    e.preventDefault();
    edSave();
  }
});

/* ===== AI 修改（类 Harness：描述需求 → LLM 生成修改 → diff 预览/应用） ===== */
let edAiResult = null;   // {path, diff, new_content}

function edAiOpen() {
  if (!edCurrent) { toast("请先从左侧打开一个文件", true); return; }
  if (edDirty && !confirm("当前文件有未保存的修改，AI 将以磁盘上的文件为准，确定继续？")) return;
  edAiResult = null;
  $("#edAiPath").textContent = edCurrent.path;
  $("#edAiInstr").value = "";
  $("#edAiDiff").textContent = "";
  $("#edAiState").textContent = "";
  $("#edAiActions").style.display = "none";
  $("#edAiModal").style.display = "flex";
  $("#edAiRun").disabled = false;
  $("#edAiInstr").focus();
}

function edAiClose() { $("#edAiModal").style.display = "none"; edAiResult = null; }

async function edAiRun() {
  const instr = $("#edAiInstr").value.trim();
  if (!instr) { toast("请先描述你想要的修改", true); return; }
  const btn = $("#edAiRun");
  btn.disabled = true;
  $("#edAiState").textContent = "⏳ AI 正在读取文件并生成修改…（大文件可能需要 1-2 分钟）";
  $("#edAiDiff").textContent = "";
  $("#edAiActions").style.display = "none";
  try {
    const r = await API.post("/api/files/ai_edit", { path: edCurrent.path, instruction: instr, apply: false });
    if (r.error) { $("#edAiState").textContent = "❌ " + r.error; toast("❌ " + r.error, true); return; }
    if (!r.changed) { $("#edAiState").textContent = "ℹ️ " + (r.note || "AI 未做修改"); return; }
    edAiResult = r;
    edRenderDiff(r.diff);
    let adds = (r.diff.match(/^\+/gm) || []).length, dels = (r.diff.match(/^-/gm) || []).length;
    if (r.diff.includes("+++ ")) adds--;
    if (r.diff.includes("--- ")) dels--;
    $("#edAiState").textContent = "✅ AI 已生成修改（+" + Math.max(adds, 0) + " / -" + Math.max(dels, 0) + " 行，模型 " + (r.model || "") + "）。请检查 diff 后点击「应用修改」。";
    $("#edAiActions").style.display = "flex";
  } catch (e) {
    $("#edAiState").textContent = "❌ " + e.message;
    toast("❌ " + e.message, true);
  } finally {
    btn.disabled = false;
  }
}

function edRenderDiff(diffText) {
  const pre = $("#edAiDiff");
  pre.textContent = "";
  const lines = (diffText || "").split("\n");
  for (const line of lines) {
    const div = document.createElement("div");
    if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) div.className = "diff-hunk";
    else if (line.startsWith("+")) div.className = "diff-add";
    else if (line.startsWith("-")) div.className = "diff-del";
    else div.className = "diff-ctx";
    div.textContent = line;
    pre.appendChild(div);
  }
  pre.scrollTop = 0;
}

async function edAiApply() {
  if (!edAiResult) return;
  const btn = $("#edAiApply");
  btn.disabled = true;
  try {
    const r = await API.post("/api/files/write", { path: edAiResult.path, content: edAiResult.new_content });
    if (r.error) { toast("❌ " + r.error, true); return; }
    edDirty = false;
    $("#edContent").value = edAiResult.new_content;
    $("#edStatus").textContent = "已保存 " + new Date().toLocaleTimeString() + "（AI 修改）";
    toast("✅ AI 修改已应用并保存: " + edAiResult.path);
    edRenderGutter();
    edAiClose();
    edRender();
  } catch (e) {
    toast("❌ 应用失败: " + e.message, true);
  } finally {
    btn.disabled = false;
  }
}

function edAiManual() {
  if (!edAiResult) return;
  edCurrent = { path: edAiResult.path, mtime: edCurrent ? edCurrent.mtime : 0 };
  edDirty = true;
  $("#edPath").value = edAiResult.path;
  $("#edContent").value = edAiResult.new_content;
  $("#edStatus").textContent = "AI 结果已填入，请手动检查后保存 (Ctrl+S)";
  edRenderGutter();
  edAiClose();
  toast("✏️ AI 结果已填入编辑器，检查后按 Ctrl+S 保存");
}

/* AI 修改事件绑定 */
$("#edAi").addEventListener("click", edAiOpen);
$("#edAiClose").addEventListener("click", edAiClose);
$("#edAiCancel").addEventListener("click", edAiClose);
$("#edAiRun").addEventListener("click", edAiRun);
$("#edAiApply").addEventListener("click", edAiApply);
$("#edAiManual").addEventListener("click", edAiManual);
$("#edAiModal").addEventListener("click", (e) => { if (e.target === $("#edAiModal")) edAiClose(); });
$("#edAiInstr").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") edAiRun();
});
