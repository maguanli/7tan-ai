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
let currentView = "dashboard";
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
    sources: loadSources, settings: loadSettings,
    code: loadCodeChanges, terminal: () => {}, logs: loadLogs, update: loadUpdate,
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
function highlightLogLine(raw) {
  const s = stripAnsi(raw == null ? "" : raw);
  if (!s || !s.trim()) return "";
  // 标准 loguru 格式: 时间 | 级别 | 模块 | 消息
  const m = s.match(/^(\d{4}-\d{2}-\d{2}[ T][\d:.]+)\s*\|\s*(DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)\s*\|\s*(.*)$/);
  if (m) {
    const time = escapeHtml(m[1]);
    const lv = m[2].toLowerCase();
    const rest = m[3];
    const pipe = rest.indexOf("|");
    let mod = "", msg = rest;
    if (pipe >= 0) { mod = escapeHtml(rest.slice(0, pipe).trim()); msg = rest.slice(pipe + 1); }
    return `<span class="cl-time">${time}</span> <span class="cl-level lv-${lv}">${m[2]}</span>` +
      (mod ? ` <span class="cl-module">${mod}</span>` : "") +
      ` <span class="cl-msg">${escapeHtml(msg)}</span>`;
  }
  // 简单行：emoji 前缀决定整行颜色
  const first = s.trim().slice(0, 2);
  const cls = CONSOLE_EMOJI_CLASS[first];
  return `<span class="cl-plain${cls ? " cl-" + cls : ""}">${escapeHtml(s)}</span>`;
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
connectWS();
loadDashboard();
loadLicenseStatus();
startLogPolling();
startConsolePolling();
// 代码变更轮询：仅当停留在 code 视图时每 10s 自动刷新
setInterval(() => { if (currentView === "code") loadCodeChanges(); }, 10000);
