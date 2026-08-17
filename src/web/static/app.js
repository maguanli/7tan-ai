/* ===== 7Tan 网页控制面板 — 前端逻辑（原生 JS，零依赖） ===== */
"use strict";

/* ---------- 工具 ---------- */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
function keyEyeSvg(open) {
  // open=true → 睁眼（当前密码掩码，点击可查看）；open=false → 闭眼（当前明文，点击可隐藏）
  // 用 SVG 而非 emoji：emoji 是彩色字体不受 color 控制，深色背景下看不见
  return open
    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
    : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
}
async function toggleKeyVis(id, btn) {
  const el = document.getElementById(id);
  if (!el) return;
  const viewId = id + "_fullview";
  const oldView = document.getElementById(viewId);
  if (oldView) {
    // 已展示明文 → 收起
    oldView.remove();
    btn.innerHTML = keyEyeSvg(true);
    btn.title = "显示明文";
    return;
  }
  // 未展示 → 从后端获取明文（前端拿到的值是脱敏的，中间是 ••••，必须调后端解密）
  btn.innerHTML = keyEyeSvg(false);
  btn.title = "隐藏明文";
  let plain = "";
  try {
    if (id === "visKey") {
      const r = await API.get("/api/settings/ai/vision-key/reveal");
      plain = (r && r.api_key) || "";
    } else {
      const cfgKey = ($("#aiConfigList") && $("#aiConfigList").value) || ($("#aiName") && $("#aiName").value) || "";
      if (!cfgKey) { toast("请先选择一个模型配置", true); btn.innerHTML = keyEyeSvg(true); btn.title = "显示明文"; return; }
      const r = await API.get("/api/settings/ai/key/reveal?config_key=" + encodeURIComponent(cfgKey));
      plain = (r && r.api_key) || "";
    }
  } catch (e) {
    const _isDown = e instanceof TypeError || /fetch|network/i.test(String(e && e.message || e));
    if (!_isDown) toast("获取明文 Key 失败: " + e.message, true);
    btn.innerHTML = keyEyeSvg(true);
    btn.title = "显示明文";
    return;
  }
  const view = document.createElement("div");
  view.id = viewId;
  view.style.cssText = "margin-top:6px;padding:8px 10px;background:#16181c;border:1px solid #3a3f47;border-radius:4px;font-family:Consolas,'Courier New',monospace;font-size:12px;line-height:1.6;color:#e8eaed;word-break:break-all;white-space:pre-wrap;user-select:text;cursor:text;";
  view.textContent = plain || "（空）";
  el.parentElement.insertAdjacentElement("afterend", view);
}

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

/* 完整时间：YYYY-MM-DD HH:MM:SS */
function fmtFullTime(d) {
  const p = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " " +
    p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
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

/* ---------- 移动端适配：内容量控制（手机不渲染/保留太多内容） ---------- */
function isMobile() {
  return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(navigator.userAgent || "");
}
const CHAT_PAGE = isMobile() ? 30 : 80;     // 对话框每页渲染条数（手机 30，桌面 80）
const CONSOLE_MAX = isMobile() ? 120 : 500;  // 实时控制台最多保留行数（手机 120，桌面 500）
const CONSOLE_LINES = isMobile() ? 60 : 150; // 控制台轮询拉取行数（手机 60，桌面 150）

/* ---------- API 封装 ---------- */
const API = {
  token: localStorage.getItem("7tan_web_token") || "",
  async req(method, path, body, timeoutMs) {
    const headers = { "Content-Type": "application/json" };
    if (this.token) headers["Authorization"] = "Bearer " + this.token;
    const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs || 12000) : null;
    let resp;
    try {
      resp = await fetch(path, {
        method,
        headers,
        body: body != null ? JSON.stringify(body) : undefined,
        signal: ctrl ? ctrl.signal : undefined,
      });
    } catch (e) {
      if (timer) clearTimeout(timer);
      const aborted = e && (e.name === "AbortError" || /abort/i.test(String(e && e.message || e)));
      if (aborted) {
        notifyServiceDown();
        throw new Error("服务无响应（可能已挂起），请点击「一键重启服务」");
      }
      if (e instanceof TypeError || /fetch|network/i.test(String(e && e.message || e))) {
        notifyServiceDown();
      }
      throw e;
    }
    if (timer) clearTimeout(timer);
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

/* ---------- 服务掉线：一键重启 ---------- */
let _svcDownNotified = 0;
function showServiceDownModal() {
  const m = $("#serviceDownModal");
  if (m) m.style.display = "flex";
}
function closeServiceDownModal() {
  const m = $("#serviceDownModal");
  if (m) m.style.display = "none";
}
function restartService() {
  const btn = $("#svcRestartBtn");
  if (btn) { btn.disabled = true; btn.textContent = "⏳ 正在重启…"; }
  API.post("/api/settings/restart", {}, 5000)
    .then(() => {
      toast("🔄 重启指令已发送，约 5 秒后自动恢复，请稍候刷新页面");
      closeServiceDownModal();
    })
    .catch(() => {
      toast("重启指令发送失败，请手动双击「启动网页版服务(Windows).bat」重启", true);
      closeServiceDownModal();
      if (btn) { btn.disabled = false; btn.textContent = "🔄 一键重启服务"; }
    });
}
function notifyServiceDown() {
  const now = Date.now();
  if (now - _svcDownNotified < 30000) return;
  _svcDownNotified = now;
  showServiceDownModal();
}

/* ---------- WebSocket（实时广播） ---------- */
let ws = null, wsRetry = 0;
function connectWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = proto + "//" + location.host + "/ws" +
    (API.token ? "?token=" + encodeURIComponent(API.token) : "");
  try { ws = new WebSocket(url); } catch (e) { scheduleReconnect(); return; }
  ws.onopen = () => {
    wsRetry = 0;
    const d = $("#connDot"); if (d) d.classList.add("on");
    const t = $("#connText"); if (t) t.textContent = "已连接";
  };
  ws.onclose = () => {
    const d = $("#connDot"); if (d) d.classList.remove("on");
    const t = $("#connText"); if (t) t.textContent = "已断开";
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

/* ---------- 移动端：侧边栏抽屉 ---------- */
function setSidebar(open) {
  const sb = document.querySelector(".sidebar");
  const mask = document.getElementById("sidebarMask");
  if (sb) sb.classList.toggle("open", !!open);
  if (mask) mask.classList.toggle("show", !!open);
}
function toggleSidebar() {
  const sb = document.querySelector(".sidebar");
  setSidebar(!(sb && sb.classList.contains("open")));
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
  // 会话列表仅在 AI 工作台时显示
  const ss = $("#sidebarSessions");
  if (ss) ss.classList.toggle("visible", view === "chat");
  refreshCurrent();
  if (window.innerWidth <= 768) setSidebar(false); // 移动端切换后自动收起抽屉
}
function refreshCurrent() {
  const fns = {
    dashboard: loadDashboard, resources: loadResources,
    tasks: loadTasks, chat: () => { loadSessions(); loadChatModels(); if (curSession) loadChatHistory(curSession); loadChatConsole(); },
    sources: loadSources, settings: loadSettings, plugins: loadMarketPlugins,
    code: loadCodeChanges, terminal: () => {}, logs: loadLogs, update: loadUpdate,
    adapt: loadAdaptView,
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
    const loggedIn = !!(d.username);
    const userEl = $("#proUser");
    if (userEl) userEl.textContent = "👤 " + (d.username || "未登录");
    const scoreEl = $("#proScore");
    if (scoreEl) scoreEl.textContent = d.score_brief ? ("⚡ 能力值: " + d.score_brief) : "⚡ 能力值: -";
    const userActions = $("#proActionsUser");
    const guestActions = $("#proActionsGuest");
    if (userActions) userActions.style.display = loggedIn ? "" : "none";
    if (guestActions) guestActions.style.display = loggedIn ? "none" : "";
  } catch (e) { /* 授权状态获取失败，静默处理 */ }
}
/* 刷新会员状态（对照桌面版 🔄 刷新） */
async function refreshLicense() {
  const btn = $("#proRefresh");
  if (!btn) return;
  try {
    btn.disabled = true; btn.textContent = "🔄 刷新中…";
    const d = await API.post("/api/license/refresh");
    toast(d.success ? "✅ " + d.message : "⚠️ " + d.message, !d.success);
  } catch (e) {
    toast("刷新失败: " + e.message, true);
  } finally {
    btn.disabled = false; btn.textContent = "🔄 刷新";
    loadLicenseStatus();
  }
}
/* 退出登录（对照桌面版 🚪 退出） */
async function logoutLicense() {
  if (!confirm("确定要退出当前会员账号吗？")) return;
  try {
    const d = await API.post("/api/license/logout");
    toast("✅ " + d.message);
  } catch (e) {
    toast("退出失败: " + e.message, true);
  } finally {
    loadLicenseStatus();
  }
}
$("#proRefresh") && $("#proRefresh").addEventListener("click", refreshLicense);
$("#proLogout") && $("#proLogout").addEventListener("click", logoutLicense);

/* 登录（弹出登录框） */
function openLoginModal() {
  const errEl = $("#loginError"); if (errEl) errEl.textContent = "";
  const u = $("#loginUser"); if (u) u.value = "";
  const p = $("#loginPwd"); if (p) p.value = "";
  const m = $("#loginModal"); if (m) m.style.display = "flex";
  setTimeout(() => { const u2 = $("#loginUser"); if (u2) u2.focus(); }, 50);
}
function closeLoginModal() {
  const m = $("#loginModal"); if (m) m.style.display = "none";
}
async function submitLogin() {
  const user = ($("#loginUser").value || "").trim();
  const pwd = $("#loginPwd").value || "";
  const remember = $("#loginRemember").checked;
  const errEl = $("#loginError");
  if (!user) { errEl.textContent = "请输入用户名或手机号"; return; }
  if (!pwd) { errEl.textContent = "请输入密码"; return; }
  const agreeEl = $("#loginAgree");
  if (agreeEl && !agreeEl.checked) { errEl.textContent = "请先勾选同意《用户协议》与《隐私政策》"; return; }
  const btn = $("#loginSubmit");
  btn.disabled = true; btn.textContent = "登录中…"; errEl.textContent = "";
  try {
    const d = await API.post("/api/license/login", { username: user, password: pwd, remember: remember });
    if (d.success) {
      toast("✅ 登录成功：" + (d.username || ""));
      closeLoginModal();
    } else {
      errEl.textContent = d.message || "登录失败";
    }
  } catch (e) {
    errEl.textContent = "登录失败: " + e.message;
  } finally {
    btn.disabled = false; btn.textContent = "登 录";
    loadLicenseStatus();
  }
}
$("#proLogin") && $("#proLogin").addEventListener("click", openLoginModal);
$("#proRegister") && $("#proRegister").addEventListener("click", () => window.open("https://www.7tan.com/bbs/register.php", "_blank"));
$("#loginSubmit") && $("#loginSubmit").addEventListener("click", submitLogin);
$("#loginClose") && $("#loginClose").addEventListener("click", closeLoginModal);
$("#loginModal") && $("#loginModal").addEventListener("click", (e) => { if (e.target === $("#loginModal")) closeLoginModal(); });
$("#loginPwd") && $("#loginPwd").addEventListener("keydown", (e) => { if (e.key === "Enter") submitLogin(); });

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
let chatModelConfigs = [];
let chatActiveKey = "";

function currentModelVal() {
  const saved = localStorage.getItem("7tan_web_model") || "";
  // 新版：localStorage 存 config_key（唯一）
  let cfg = chatModelConfigs.find((c) => c.config_key === saved);
  if (cfg) return cfg.config_key;
  // 兼容旧数据：localStorage 存的是 model 名
  cfg = chatModelConfigs.find((c) => (c.model || c.config_key) === saved);
  if (cfg) return cfg.config_key;
  // 回退：当前启用配置 → 第一个配置
  const activeCfg = chatModelConfigs.find((c) => c.config_key === chatActiveKey) || chatModelConfigs[0] || {};
  return activeCfg.config_key || (activeCfg.model || "");
}

// 当前选中配置的模型名（发送给后端用；config_key 仅用于 UI 唯一标识）
function currentModelName() {
  const key = $("#chatModelSelect").value || currentModelVal();
  const cfg = chatModelConfigs.find((c) => c.config_key === key) || {};
  return cfg.model || key || null;
}

function renderModelSelect() {
  const sel = $("#chatModelSelect");
  if (!sel) return;
  if (!chatModelConfigs.length) { sel.innerHTML = '<option value="">无模型配置</option>'; return; }
  const curKey = currentModelVal();
  // ★ = 设置页启用的模型（chatActiveKey，与数据库 is_active 一致）
  // selected = 用户当前选择的聊天模型（localStorage）
  sel.innerHTML = chatModelConfigs.map((c) => {
    const key = c.config_key || (c.model || "");
    const label = c.config_key + (c.model && c.model !== c.config_key ? " · " + c.model : "") + (c.config_key === chatActiveKey ? " ★" : "");
    return `<option value="${escapeHtml(key)}" ${key === curKey ? "selected" : ""}>${escapeHtml(label)}</option>`;
  }).join("");
  localStorage.setItem("7tan_web_model", curKey);
}

async function loadChatModels() {
  try {
    const d = await API.get("/api/settings");
    const ai = (d.settings && d.settings.ai) || {};
    chatModelConfigs = Object.values(ai.configs || {});
    chatActiveKey = ai.active || "";
    // 同步：AI工作台「当前模型」跟随设置页启用的模型（数据库是唯一事实源，保证两端一致）
    if (chatActiveKey) localStorage.setItem("7tan_web_model", chatActiveKey);
    renderModelSelect();
  } catch (e) { const sel = $("#chatModelSelect"); if (sel) sel.innerHTML = '<option value="">模型加载失败</option>'; toast("模型列表加载失败: " + e.message, true); }
}

$("#chatModelSelect").addEventListener("change", () => {
  const newKey = $("#chatModelSelect").value;
  localStorage.setItem("7tan_web_model", newKey);
  // 同步到设置页：切换工作台模型 = 启用该模型（保持两端一致）
  chatActiveKey = newKey;
  API.put("/api/settings", { ai: { active: newKey } }).catch(() => {});
  renderModelSelect();
});
function _fmtSideTime(ts) {
  if (!ts) return "";
  try {
    const d = new Date(ts.replace("T", " ").slice(0, 19).replace(/-/g, "/"));
    const now = new Date();
    if (d.toDateString() === now.toDateString())
      return d.toTimeString().slice(0, 5); // HH:MM
    if (d.getFullYear() === now.getFullYear())
      return (d.getMonth() + 1 + "").padStart(2, "0") + "-" + (d.getDate() + "").padStart(2, "0") + " " + d.toTimeString().slice(0, 5);
    return d.getFullYear() + "-" + ((d.getMonth() + 1) + "").padStart(2, "0") + "-" + (d.getDate() + "").padStart(2, "0");
  } catch (e) { return ts.slice(0, 10); }
}
async function loadSessions() {
  try {
    const d = await API.get("/api/chat/history");
    const sessions = d.sessions || [];
    const el = $("#sessionList");
    if (!el) return;
    el.innerHTML = sessions.map((s) => {
      const fullTitle = s.title || s.session_id;
      const title = fullTitle.slice(0, 20);
      const time = _fmtSideTime(s.last_activity || s.updated_at);
      const cnt = Number(s.message_count) || 0;
      return `<div class="sidebar-session-item ${s.session_id === curSession ? "active" : ""}" data-full-title="${escapeHtml(fullTitle)}" data-count="${cnt}" onclick="selectSession('${s.session_id}')">
        <span class="s-title">💬 ${escapeHtml(title)}</span>
        <span class="s-time">${escapeHtml(time)}</span>
        <span class="s-del" title="删除会话" onclick="event.stopPropagation();deleteSession('${s.session_id}')">✕</span>
      </div>`;
    }).join("") || '<div class="muted" style="padding:12px;text-align:center">暂无会话</div>';
    _bindSessionTooltip(el);
    const cnt = $("#sessionCount");
    if (cnt) cnt.textContent = sessions.length + " 条对话";
  } catch (e) { toast("会话加载失败: " + e.message, true); }
}

/* 会话悬停提示：显示完整标题 + 消息条数（事件委托，列表刷新后依然生效） */
function _bindSessionTooltip(el) {
  if (!el || el.dataset.tipBound) return;
  el.dataset.tipBound = "1";
  el.addEventListener("mouseover", (ev) => {
    const item = ev.target.closest(".sidebar-session-item");
    if (item) _showSessionTooltip(item, ev);
  });
  el.addEventListener("mouseout", (ev) => {
    const item = ev.target.closest(".sidebar-session-item");
    if (!item || !item.contains(ev.relatedTarget)) _hideSessionTooltip();
  });
  el.addEventListener("mouseleave", _hideSessionTooltip);
}
function _showSessionTooltip(item, ev) {
  let tip = document.getElementById("sessionTooltip");
  if (!tip) {
    tip = document.createElement("div");
    tip.id = "sessionTooltip";
    tip.className = "session-tooltip";
    document.body.appendChild(tip);
  }
  const full = item.dataset.fullTitle || "";
  const cnt = item.dataset.count || "0";
  tip.innerHTML = `<div class="t-title">💬 ${escapeHtml(full)}</div><div class="t-count">${cnt} 条对话</div>`;
  tip.style.display = "block";
  const pad = 14;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  const r = tip.getBoundingClientRect();
  if (x + r.width > window.innerWidth - 8) x = Math.max(8, ev.clientX - r.width - pad);
  if (y + r.height > window.innerHeight - 8) y = Math.max(8, ev.clientY - r.height - pad);
  tip.style.left = x + "px";
  tip.style.top = y + "px";
}
function _hideSessionTooltip() {
  const tip = document.getElementById("sessionTooltip");
  if (tip) tip.style.display = "none";
}
async function selectSession(sid) {
  curSession = sid;
  loadSessions();
  await loadChatHistory(sid);
}
/* 对话消息分页渲染（移动端友好：不全量渲染，可“加载更早”） */
let chatAllMsgs = [];      // 当前会话完整消息缓存
let chatLoadedCount = 0;   // 已渲染的消息条数
function msgToHtml(m, idx) {
  const who = m.role === "user" ? "我" : (m.model || "AI");
  return `<div class="msg ${m.role === "user" ? "user" : "assistant"}" data-idx="${idx}" data-raw="${escapeHtml(m.content || "")}">
    <div class="msg-body">${renderMarkdown(m.content || "")}</div>
    <span class="meta">${escapeHtml(who)} · ${fmtTime(m.created_at)}</span>
    <div class="msg-actions">
      <button class="msg-act" onclick="copyMsg(this)">复制</button>
      <button class="msg-act" onclick="editMsg(this)">编辑</button>
      <button class="msg-act danger" onclick="delMsg(this)">删除</button>
    </div>
  </div>`;
}
function renderChatWindow() {
  const box = $("#chatMessages");
  if (!box) return;
  const total = chatAllMsgs.length;
  if (!total) { box.innerHTML = '<div class="muted center">空会话</div>'; return; }
  const shown = Math.min(total, Math.max(chatLoadedCount || 0, CHAT_PAGE));
  const start = total - shown;
  const extra = start;
  let html = "";
  if (extra > 0) {
    html += `<div class="chat-load-more"><button id="chatLoadMore" class="btn btn-sm">⬆️ 加载更早 ${Math.min(extra, CHAT_PAGE)} 条（还剩 ${extra} 条）</button></div>`;
  }
  html += chatAllMsgs.slice(start).map((m, i) => msgToHtml(m, start + i)).join("");
  box.innerHTML = html;
  const btn = $("#chatLoadMore");
  if (btn) btn.onclick = () => { chatLoadedCount = shown + CHAT_PAGE; renderChatWindow(); };
  box.scrollTop = box.scrollHeight;
}
async function loadChatHistory(sid) {
  if (!sid) { $("#chatMessages").innerHTML = '<div class="muted center">选择或新建一个会话开始对话</div>'; return; }
  try {
    const d = await API.get("/api/chat/history?session_id=" + encodeURIComponent(sid));
    const msgs = d.messages || [];
    chatAllMsgs = msgs;
    chatLoadedCount = 0;
    renderChatWindow();
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
let chatAbortCtrl = null;   // 当前流式请求的 AbortController（点"中止"时立即断开）
let voiceEnabled = false;
let voiceGender = "male"; // male / female
function updateSendBtn() {
  const btn = $("#chatSend");
  if (chatSending) { btn.textContent = "中止"; btn.className = "btn btn-send abort"; }
  else { btn.textContent = "发送 ▲"; btn.className = "btn btn-send"; }
}
function speakText(text) {
  if (!voiceEnabled || !text) return;
  try {
    const synth = window.speechSynthesis;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[#*`>\-\[\]()]/g, "").substring(0, 500));
    u.lang = "zh-CN";
    u.rate = 1; u.pitch = 1;
    const voices = synth.getVoices();
    const zhVoices = voices.filter(v => v.lang.startsWith("zh"));
    if (zhVoices.length) {
      // 尝试按性别选
      const want = voiceGender === "male" ? /male|男|yunxi|yangyang/i : /female|女|xiaoxiao|xiaoyi/i;
      const found = zhVoices.find(v => want.test(v.name) || want.test(v.voiceURI));
      u.voice = found || zhVoices[0];
    }
    synth.speak(u);
  } catch (e) { console.warn("TTS failed", e); }
}
/* ---------- 聊天图片附件（选择/粘贴/拖拽/上传） ---------- */
let chatImageFile = null;   // 待发送的图片 File
let chatImageDataUrl = null; // 本地预览 dataURL

function setChatImage(file) {
  if (!file) return;
  if (!/^image\//.test(file.type)) { toast("请选择图片文件", true); return; }
  if (file.size > 10 * 1024 * 1024) { toast("图片不能超过 10MB", true); return; }
  chatImageFile = file;
  // 选图/拖图后把焦点放回输入框：用户可直接回车发送（防止焦点留在📎按钮上，回车无效或再次弹出文件选择框）
  setTimeout(() => { const inp = $("#chatInput"); if (inp) inp.focus(); }, 0);
  const rd = new FileReader();
  rd.onload = (e) => {
    if (chatImageFile !== file) return; // 竞态防护：图片已被清除/替换时丢弃迟到的预览
    chatImageDataUrl = e.target.result;
    const pv = $("#chatAttachPreview"); if (pv) pv.src = chatImageDataUrl;
    const nm = $("#chatAttachName"); if (nm) nm.textContent = file.name + " (" + fmtSize(file.size) + ")";
    const row = $("#chatAttachRow"); if (row) row.style.display = "flex";
  };
  rd.onerror = () => { toast("图片读取失败", true); };
  rd.readAsDataURL(file);
}

function clearChatImage() {
  chatImageFile = null;
  chatImageDataUrl = null;
  const row = $("#chatAttachRow"); if (row) row.style.display = "none";
  const fi = $("#chatImageFile"); if (fi) fi.value = "";
}

function bindChatImageEvents() {
  const btn = $("#chatImageBtn");
  if (btn) btn.addEventListener("click", () => { const fi = $("#chatImageFile"); if (fi) fi.click(); });
  const fi = $("#chatImageFile");
  if (fi) fi.addEventListener("change", (e) => setChatImage(e.target.files && e.target.files[0]));
  const rm = $("#chatAttachRemove");
  if (rm) rm.addEventListener("click", clearChatImage);
  // 粘贴截图（Ctrl+V）
  const input = $("#chatInput");
  if (input) input.addEventListener("paste", (e) => {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    for (const it of items) {
      if (it.type && it.type.startsWith("image/")) {
        const f = it.getAsFile();
        if (f) { e.preventDefault(); setChatImage(f); return; }
      }
    }
  });
  // 拖拽图片到输入区
  const zone = document.querySelector(".chat-inputbar");
  if (zone) {
    ["dragover", "dragenter"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("drag-over"); }));
    ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("drag-over"); }));
    zone.addEventListener("drop", (e) => {
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) setChatImage(f);
    });
  }
}
bindChatImageEvents();

// 兜底：焦点落在聊天区📎按钮上时，输入区有内容则回车=发送（防止"选完图焦点在按钮上，回车没反应/又弹出文件选择框"）
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.shiftKey) return;
  const t = e.target;
  if (t && t.id === "chatImageBtn") {
    const text = $("#chatInput").value.trim();
    if (text || chatImageFile) { e.preventDefault(); sendChat(); }
  }
});

async function sendChat() {
  if (chatSending) { abortChat(); return; } // 发送中点击=中止
  const text = $("#chatInput").value.trim();
  if (!text && !chatImageFile) return;
  if (!curSession) { toast("请先新建或选择会话", true); return; }
  chatSending = true;
  updateSendBtn();
  $("#chatInput").value = "";
  // 若有图片：先上传，获取服务器路径（供视觉分析）
  let imagePath = null;
  if (chatImageFile) {
    const fd = new FormData();
    fd.append("file", chatImageFile);
    const hdrs = {};
    if (API.token) hdrs["Authorization"] = "Bearer " + API.token;
    let upResp;
    try {
      upResp = await fetch("/api/chat/upload", { method: "POST", headers: hdrs, body: fd });
    } catch (e) { toast("图片上传失败: " + e.message, true); chatSending = false; updateSendBtn(); return; }
    if (!upResp.ok) {
      let m = "图片上传失败";
      try { const j = await upResp.json(); m = j.detail || m; } catch (e) {}
      toast(m, true); chatSending = false; updateSendBtn(); return;
    }
    try { const upj = await upResp.json(); imagePath = upj.path || null; } catch (e) {}
  }
  const um = appendMsg("user", text);
  um.body.innerHTML = (chatImageDataUrl ? `<img class="msg-img" src="${chatImageDataUrl}" alt="图片">` : "") + renderMarkdown(text);
  um.meta.textContent = "我 · " + fmtFullTime(new Date());
  clearChatImage(); // 消息已上屏，立即清理输入框附件（图片保留在消息气泡中）
  // 同步用户消息到缓存（供分页渲染）
  if (chatAllMsgs) chatAllMsgs.push({ role: "user", content: text, created_at: fmtFullTime(new Date()) });
  const p = appendMsg("assistant", "⏳ AI 思考中…（流式输出即将开始）", "pending streaming");
  p.body.textContent = "⏳ AI 思考中…（流式输出即将开始）";
  let acc = "", doneModel = "";
  try {
    const headers = { "Content-Type": "application/json" };
    if (API.token) headers["Authorization"] = "Bearer " + API.token;
    // 创建中止控制器：点"中止"时前端立即断开流式连接（后端收到断开也会自动停 agent）
    chatAbortCtrl = new AbortController();
    const resp = await fetch("/api/chat/send/stream", {
      method: "POST",
      headers,
      signal: chatAbortCtrl.signal,
      body: JSON.stringify({ session_id: curSession, message: text, model: currentModelName(), image_path: imagePath }),
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
          p.div.classList.remove("pending");
          p.div.dataset.raw = acc;
          p.body.innerHTML = renderMarkdown(acc) + '<span class="cursor">▍</span>';
          const box = $("#chatMessages"); box.scrollTop = box.scrollHeight;
        } else if (ev.type === "done") {
          acc = ev.result || acc;
          doneModel = ev.model || doneModel;
        } else if (ev.type === "error") {
          throw new Error(ev.message || "AI 出错");
        } else if (ev.type === "session_id") {
          curSession = ev.session_id;
        }
      }
    }
    p.div.classList.remove("pending", "streaming");
    p.div.dataset.raw = acc;
    p.body.innerHTML = renderMarkdown(acc);
    p.meta.textContent = (doneModel || currentModelName() || "AI") + " · " + fmtFullTime(new Date());
  } catch (e) {
    const aborted = (e && e.name === "AbortError") || /abort/i.test(String((e && e.message) || ""));
    if (aborted) {
      // 用户主动中止：保留已输出的部分，标记为已中止
      p.div.classList.remove("pending", "streaming");
      if (acc) { p.div.dataset.raw = acc; p.body.innerHTML = renderMarkdown(acc); }
      else { p.div.dataset.raw = "⏹ 已中止"; p.body.textContent = "⏹ 已中止"; }
      p.meta.textContent = "已中止 · " + fmtFullTime(new Date());
    } else {
      if (acc) { p.div.dataset.raw = acc; p.body.innerHTML = renderMarkdown(acc); }
      else { p.div.dataset.raw = "❌ " + e.message; p.body.textContent = "❌ " + e.message; }
      p.div.classList.add("error");
    }
  } finally {
    chatAbortCtrl = null;
    chatSending = false;
    updateSendBtn();
    clearChatImage(); // 发送结束，清理附件预览（图片已留在用户消息气泡中）
    // 语音朗读 AI 回复
    // 语音朗读由后端 TTS 完成（agent_loop 最终回复 → speak_bridge → Piper/Edge），前端不再调用浏览器 Web Speech API
    // 同步 AI 回复到缓存（供分页渲染）
    if (chatAllMsgs) chatAllMsgs.push({ role: "assistant", content: p.div.dataset.raw || acc || "", model: doneModel || currentModelName() || "AI", created_at: fmtFullTime(new Date()) });
    const box = $("#chatMessages"); box.scrollTop = box.scrollHeight;
  }
}
function appendMsg(role, text, extra) {
  const box = $("#chatMessages");
  const div = document.createElement("div");
  div.className = "msg " + role + (extra ? " " + extra : "");
  div.dataset.raw = text || "";
  const body = document.createElement("div");
  body.className = "msg-body";
  div.appendChild(body);
  const meta = document.createElement("span");
  meta.className = "meta";
  div.appendChild(meta);
  const actions = document.createElement("div");
  actions.className = "msg-actions";
  actions.innerHTML = '<button class="msg-act" onclick="copyMsg(this)">复制</button><button class="msg-act" onclick="editMsg(this)">编辑</button><button class="msg-act danger" onclick="delMsg(this)">删除</button>';
  div.appendChild(actions);
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return { div, body, meta };
}

/* ---------- 消息操作：复制 / 编辑 / 删除 ---------- */
let editMsgTarget = null;
function fallbackCopy(text, done) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand("copy"); } catch (e) {}
  document.body.removeChild(ta);
  done();
}
function copyMsg(btn) {
  const msg = btn.closest(".msg");
  const raw = (msg && msg.dataset.raw) || "";
  const done = () => { btn.textContent = "已复制"; setTimeout(() => { btn.textContent = "复制"; }, 1500); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(raw).then(done).catch(() => fallbackCopy(raw, done));
  } else {
    fallbackCopy(raw, done);
  }
}
function editMsg(btn) {
  const msg = btn.closest(".msg");
  if (!msg) return;
  editMsgTarget = msg;
  $("#editMsgText").value = msg.dataset.raw || "";
  $("#editMsgModal").style.display = "flex";
  setTimeout(() => { const t = $("#editMsgText"); if (t) { t.focus(); } }, 50);
}
function closeEditMsg() {
  $("#editMsgModal").style.display = "none";
  editMsgTarget = null;
}
function saveEditMsg() {
  if (!editMsgTarget) return;
  const newText = $("#editMsgText").value;
  editMsgTarget.dataset.raw = newText;
  const body = editMsgTarget.querySelector(".msg-body");
  if (body) body.innerHTML = renderMarkdown(newText);
  // 同步到消息缓存（供分页渲染）
  const eidx = parseInt(editMsgTarget.dataset.idx, 10);
  if (!isNaN(eidx) && chatAllMsgs && chatAllMsgs[eidx]) chatAllMsgs[eidx].content = newText;
  closeEditMsg();
  toast("✅ 已更新消息");
}
function delMsg(btn) {
  const msg = btn.closest(".msg");
  if (!msg) return;
  if (!confirm("确定要删除这条消息吗？")) return;
  // 同步从消息缓存移除（供分页渲染）
  const didx = parseInt(msg.dataset.idx, 10);
  if (!isNaN(didx) && chatAllMsgs && chatAllMsgs[didx]) chatAllMsgs.splice(didx, 1);
  msg.remove();
}
// 🛡️ 页面关闭/刷新时主动通知后端中止任务（防 SSE 断连检测失效导致后台空转）
window.addEventListener('pagehide', () => {
  if (chatSending && curSession) {
    try {
      const url = '/api/chat/abort/' + encodeURIComponent(curSession);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url);
      } else {
        fetch(url, { method: 'POST', keepalive: true });
      }
    } catch (e) {}
  }
});

async function abortChat() {
  // 1) 关键：立即断开前端流式 fetch，马上恢复按钮状态（不再等后端响应）
  if (chatAbortCtrl) {
    try { chatAbortCtrl.abort(); } catch (e) {}
  }
  // 2) 兜底：无论 fetch 是否正常中断，都立刻复位按钮状态，防止卡在"中止"
  chatAbortCtrl = null;
  chatSending = false;
  updateSendBtn();
  // 3) 通知后端停止生成（尽力而为，快速超时 1.5s；后端即使无任务/断开也不影响前端）
  if (curSession) {
    try {
      const c = new AbortController();
      const t = setTimeout(() => c.abort(), 1500);
      await fetch("/api/chat/abort/" + encodeURIComponent(curSession), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: c.signal,
      }).catch(() => {});
      clearTimeout(t);
    } catch (e) { /* 后端可能已断开或没有执行中的任务，忽略 */ }
  }
  toast("⏹ 已中止");
}
$("#chatSend").addEventListener("click", sendChat);
function renderVoiceUI() {
  const vt = $("#voiceToggle"), vg = $("#voiceGender");
  if (vt) { vt.textContent = voiceEnabled ? "🔊 语音中" : "🔇 语音"; vt.classList.toggle("on", voiceEnabled); }
  if (vg) { vg.textContent = voiceGender === "female" ? "♀ 女声" : "♂ 男声"; vg.classList.toggle("male", voiceGender === "male"); }
}
async function loadVoiceSettings() {
  try {
    const d = await API.get("/api/chat/voice");
    voiceEnabled = !!d.mode;
    voiceGender = d.gender === "female" ? "female" : "male";
  } catch (e) { /* 后端无该接口时静默 */ }
  renderVoiceUI();
}
async function syncVoiceSettings() {
  try { await API.post("/api/chat/voice", { mode: voiceEnabled, gender: voiceGender }); }
  catch (e) { toast("语音设置同步失败: " + e.message, true); }
}
$("#voiceToggle").addEventListener("click", function() {
  voiceEnabled = !voiceEnabled;
  renderVoiceUI();
  syncVoiceSettings();
  toast(voiceEnabled ? "语音朗读已开启" : "语音朗读已关闭");
});
$("#voiceGender").addEventListener("click", function() {
  voiceGender = voiceGender === "male" ? "female" : "male";
  renderVoiceUI();
  syncVoiceSettings();
  toast(voiceGender === "female" ? "已切换为女声" : "已切换为男声");
});
// 预加载语音列表
if (window.speechSynthesis) { speechSynthesis.getVoices(); speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices(); }
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
    // 更新前检测用户是否已在底部
    const atBottom = out.scrollHeight - out.scrollTop - out.clientHeight < 60;
    out.textContent = lines.length ? lines.join("\n") : "（暂无日志）";
    // 只有原本在底部才自动滚到底
    if (logAutoRefresh && atBottom) out.scrollTop = out.scrollHeight;
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
  // 更新前检测用户是否已在底部（距底 < 60px 视为"在看最新日志"）
  const atBottom = out.scrollHeight - out.scrollTop - out.clientHeight < 60;
  out.innerHTML = consoleBuf.length
    ? consoleBuf.join("\n")
    : '<span class="cl-empty">（暂无日志）</span>';
  // 只有原本在底部才自动滚到底，用户手动往上看了就不打扰
  if (atBottom) out.scrollTop = out.scrollHeight;
}
function appendConsole(text) {
  if (!text) return;
  const out = $("#consoleOutput");
  if (!out || consolePaused) return;
  const MAX = CONSOLE_MAX;
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
    const d = await API.get("/api/logs/recent?lines=" + CONSOLE_LINES + "&source=ring");
    const lines = d.lines || [];
    consoleBuf = lines.map(highlightLogLine).filter(Boolean);
    if (consoleBuf.length > CONSOLE_MAX) consoleBuf = consoleBuf.slice(-CONSOLE_MAX);
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
$("#consoleClear").addEventListener("click", async () => {
  // 修复：清空必须同时清 前端内存缓冲 consoleBuf + 后端环形缓冲 _LOG_RING，
  // 否则 3 秒轮询 /api/logs/recent 会把旧日志重新拉回来（表现为"点清空没清掉"）
  consoleBuf = [];
  try { await API.post("/api/logs/clear"); } catch (e) { /* 后端清空失败不阻断前端 */ }
  renderConsole();
});
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
const menuBtn = document.getElementById("menuBtn");
if (menuBtn) menuBtn.addEventListener("click", toggleSidebar);
const sidebarMaskEl = document.getElementById("sidebarMask");
if (sidebarMaskEl) sidebarMaskEl.addEventListener("click", () => setSidebar(false));
window.addEventListener("resize", () => { if (window.innerWidth > 768) setSidebar(false); });
$("#tokenInput").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#tokenBtn").click(); });
initSettingsTabs();
connectWS();
switchView("chat");
loadLicenseStatus();
loadVoiceSettings();
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
  $("#aiProvider").addEventListener("change", (e) => _onProviderChange(e.target.value));
  $("#aiQuickGlm").addEventListener("click", quickAddGlmFlash);
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
  $("#remoteToggleToken").addEventListener("click", toggleRemoteToken);
  $("#remoteCopyToken").addEventListener("click", copyRemoteToken);
  $("#remoteRegenToken").addEventListener("click", regenerateRemoteToken);
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
  loadRemote();
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
/* 提供商切换时自动填写 Base URL 和默认模型 */
function _onProviderChange(provider) {
  const presets = {
    deepseek:  { base: "https://api.deepseek.com/v1",              model: "" },
    openai:    { base: "https://api.openai.com/v1",                model: "" },
    zhipu:     { base: "https://open.bigmodel.cn/api/paas/v4",     model: "glm-4-flash" },
    moonshot:  { base: "https://api.moonshot.cn/v1",               model: "" },
    siliconflow:{ base: "https://api.siliconflow.cn/v1",           model: "" },
    doubao:    { base: "https://ark.cn-beijing.volces.com/api/v3", model: "" },
    qwen:      { base: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "" },
    mimo:      { base: "https://api.mimo.ai/v1",                   model: "" },
    ollama:    { base: "http://localhost:11434/v1",                 model: "" },
  };
  const p = presets[provider];
  if (p) {
    if (p.base) $("#aiBase").value = p.base;
    if (p.model) $("#aiModel").value = p.model;
  }
}
/* 一键添加 GLM-4.7-Flash */
async function quickAddGlmFlash() {
  const key = "zhipu";
  const cfg = { provider: "zhipu", model: "glm-4-flash", api_key: "", base_url: "https://open.bigmodel.cn/api/paas/v4" };
  if (!aiConfigsCache) aiConfigsCache = {};
  if (aiConfigsCache[key]) {
    toast("配置「zhipu」已存在，请在左侧列表选择编辑", true);
    refreshAiList(key);
    return;
  }
  aiConfigsCache[key] = cfg;
  refreshAiList(key);
  toast("✅ 已新建 GLM-4.7-Flash 配置，请填写 API Key 后点保存");
}
async function deleteAiConfig() {
  const key = $("#aiConfigList").value;
  if (!key) return;
  if (!aiConfigsCache || !aiConfigsCache[key]) { delete aiConfigsCache[key]; refreshAiList(Object.keys(aiConfigsCache)[0] || ""); toast("已删除本地未保存配置"); return; }
  if (!confirm(`确定删除 AI 配置「${key}」？`)) return;
  const wasActive = (key === aiActiveKey);
  delete aiConfigsCache[key];
  const first = Object.keys(aiConfigsCache)[0] || "";
  refreshAiList(first);
  try {
    await API.put("/api/settings", { ai: { deleted: [key], active: wasActive ? first : aiActiveKey } });
    if (wasActive) { aiActiveKey = first; refreshAiList(first); loadChatModels(); }
    toast("✅ 已删除配置 " + key);
  } catch (e) { toast("删除失败: " + e.message, true); loadAiSettings(); }
}
async function activateAiConfig() {
  const key = $("#aiConfigList").value;
  if (!key) return;
  if (!aiConfigsCache || !aiConfigsCache[key]) { toast("该配置尚未保存到数据库，请先点「保存模型配置」", true); return; }
  aiActiveKey = key;
  refreshAiList(key);
  try {
    await API.put("/api/settings", { ai: { active: key } });
    toast("✅ 已启用模型 " + key);
    loadChatModels();
  } catch (e) { toast("启用失败: " + e.message, true); loadAiSettings(); }
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
    loadChatModels();
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
      "【出品】老马",
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
/* --- 远程访问 --- */
let remoteTokenPlain = "";
async function loadRemote() {
  try {
    const d = await API.get("/api/settings/remote");
    const port = d.port || 9900;
    const ips = (d.lan_ips || []).filter(Boolean);
    const localUrl = "http://127.0.0.1:" + port + "/";
    const lanUrls = ips.map(ip => "http://" + ip + ":" + port + "/");
    remoteTokenPlain = d.token || "";
    const masked = d.token_masked || "";
    $("#remoteToken").value = masked || "";
    $("#remoteToken").type = "password";
    $("#remoteTokenMsg").textContent = "";

    $("#remoteInfo").innerHTML = [
      "<label>本机访问 <input value='" + escapeHtml(localUrl) + "' readonly></label>",
      "<label>局域网访问（手机/平板）<textarea rows='" + Math.max(1, lanUrls.length) + "' readonly style='width:100%;box-sizing:border-box;font-family:monospace'>" + escapeHtml(lanUrls.join("\n") || "（未检测到局域网 IP）") + "</textarea></label>",
      "<label>监听地址 <input value='" + escapeHtml(String(d.host || "0.0.0.0")) + ":" + port + "' readonly></label>",
      "<div class='toolbar' style='margin-top:8px;flex-wrap:wrap;gap:8px'><label style='display:flex;align-items:center;gap:8px;white-space:normal'><input type='checkbox' id='remoteAllowLan' " + (d.allow_lan ? "checked" : "") + "> 局域网免 Token（私有网段设备直接访问，无需输入 Token）</label><button id='remoteSaveLan' class='btn btn-sm btn-primary'>💾 保存开关</button><span class='muted' id='remoteLanMsg'></span></div>",
    ].join("");
    $("#remoteSaveLan").addEventListener("click", saveRemoteLan);

    // 外网访问面板
    const tools = d.tunnel_tools || [];
    const toolText = tools.length ? "检测到正在运行：" + tools.map(escapeHtml).join("、") : "未检测到内网穿透工具（frp / cpolar / ngrok / cloudflared 等）";
    $("#remoteWan").innerHTML = [
      "<div class='muted' style='margin-bottom:8px'>🔍 " + toolText + "</div>",
      "<details open><summary style='cursor:pointer'>📡 方案一：内网穿透（推荐，免费）</summary>",
      "<div class='form' style='margin-top:6px'>",
      "<p class='muted'>让外网通过一个公网地址访问本机服务，无需公网 IP。常用工具及命令：</p>",
      "<label>① Cloudflare Tunnel（免费、稳定）<input value='cloudflared tunnel --url http://127.0.0.1:" + port + "' readonly></label>",
      "<label>② cpolar（国内访问快）<input value='cpolar http " + port + "' readonly></label>",
      "<label>③ frp（需一台有公网 IP 的服务器）<input value='frpc -c frpc.ini  # 服务端 frps 配置见 frp 文档' readonly></label>",
      "<p class='muted' style='margin-top:6px'>⚠️ 外网访问<b>始终需要 API Token</b>（即使开启局域网免 Token 也只放行局域网）。启动穿透后，把生成的公网地址填到手机浏览器即可。</p>",
      "</div></details>",
      "<details><summary style='cursor:pointer'>☁️ 方案二：云服务器部署</summary>",
      "<div class='form' style='margin-top:6px'>",
      "<p class='muted'>将 WEB 版部署到云服务器（腾讯云/阿里云轻量等），通过服务器公网 IP:" + port + " 访问；记得在服务器安全组放行 " + port + " 端口。</p>",
      "</div></details>",
      "<details><summary style='cursor:pointer'>🔗 方案三：异地组网（Tailscale / ZeroTier）</summary>",
      "<div class='form' style='margin-top:6px'>",
      "<p class='muted'>在电脑和手机上都安装 Tailscale / ZeroTier 并登录同一账号，手机用分配的虚拟 IP:" + port + " 访问。无需公网 IP，也无需穿透。</p>",
      "</div></details>",
    ].join("");
  } catch (e) {
    $("#remoteInfo").innerHTML = "<span class='muted'>加载失败: " + escapeHtml(e.message) + "</span>";
  }
}
async function saveRemoteLan() {
  const on = $("#remoteAllowLan").checked;
  try {
    await API.put("/api/settings/remote", { allow_lan: on });
    $("#remoteLanMsg").textContent = "已保存，重启服务后生效";
    toast(on ? "✅ 已开启局域网免 Token（重启服务后生效）" : "已关闭局域网免 Token（重启服务后生效）");
  } catch (e) { toast("保存失败: " + e.message, true); }
}
function toggleRemoteToken() {
  const el = $("#remoteToken");
  if (el.type === "password") {
    el.type = "text";
    el.value = remoteTokenPlain || el.value;
  } else {
    el.type = "password";
    el.value = remoteTokenPlain ? remoteTokenPlain.slice(0, 3) + "••••" + remoteTokenPlain.slice(-3) : el.value;
  }
}
async function copyRemoteToken() {
  if (!remoteTokenPlain) { toast("Token 为空", true); return; }
  try {
    await navigator.clipboard.writeText(remoteTokenPlain);
    toast("📋 已复制 Token");
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.value = remoteTokenPlain;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    toast("📋 已复制 Token");
  }
}
async function regenerateRemoteToken() {
  if (!confirm("重新生成 API Token 后，旧 Token 立即失效（重启服务后生效）。确定继续？")) return;
  try {
    const d = await API.post("/api/settings/remote/regenerate-token");
    remoteTokenPlain = d.token || "";
    $("#remoteToken").value = remoteTokenPlain ? remoteTokenPlain.slice(0, 3) + "••••" + remoteTokenPlain.slice(-3) : "";
    $("#remoteToken").type = "password";
    $("#remoteTokenMsg").textContent = "✅ 已重新生成，重启服务后生效";
    toast("🔄 Token 已重新生成（重启后生效）");
  } catch (e) { toast("重新生成失败: " + e.message, true); }
}
async function loadAboutUpdate() {
  const msg = $("#aboutUpdateMsg");
  msg.textContent = "检查中…";
  try {
    const d = await API.get("/api/update/check");
    msg.textContent = d.has_update ? `发现新版本 v${escapeHtml((d.latest || {}).version || "")}` : `✅ 已是最新版本 v${escapeHtml(d.current)}`;
  } catch (e) { msg.textContent = "检查失败: " + e.message; }
}

/* ===== 平台适配（插件复制适配向导）===== */
let adaptTimer = null;
let adaptRunning = false;

async function loadAdaptView() {
  // 清除旧轮询
  if (adaptTimer) { clearInterval(adaptTimer); adaptTimer = null; }
  try {
    // 1) 体检（当前系统 + 插件兼容性）
    const data = await API.req("GET", "/api/adapt/check");
    if (data.error) {
      $("#adaptSystemInfo").textContent = "体检失败: " + data.error;
      return;
    }
    renderAdaptSystem(data);
    renderAdaptPlugins(data.plugins || []);

    // 2) 状态（是否正在运行 / 历史报告）
    const st = await API.req("GET", "/api/adapt/status");
    renderAdaptStatus(st, data);
  } catch (e) {
    $("#adaptSystemInfo").textContent = "加载失败: " + e.message;
  }
}

function renderAdaptSystem(data) {
  const st = data.stats || {};
  const info = [
    "<b>当前系统：</b>" + escapeHtml(data.platform_name || data.platform || "?") +
    " &nbsp;|&nbsp; <b>详情：</b>" + escapeHtml(data.os_detail || "") +
    " &nbsp;|&nbsp; <b>Python：</b>" + escapeHtml(data.python || ""),
    "<b>插件总数：</b>" + (data.total || 0) +
    " &nbsp;✅ 原生兼容 <b style='color:#2e7d32'>" + (st.ok || 0) + "</b>" +
    " &nbsp;🔄 可适配 <b style='color:#e65100'>" + (st.adaptable || 0) + "</b>" +
    " &nbsp;⏭️ 跳过 <b style='color:#888'>" + (st.skipped || 0) + "</b>" +
    " &nbsp;❌ 缺失 <b style='color:#c62828'>" + (st.missing || 0) + "</b>",
  ].join("<br>");
  $("#adaptSystemInfo").innerHTML = info;
}

function renderAdaptPlugins(plugins) {
  const rows = plugins.map((p) => {
    const icon = { ok: "✅", adaptable: "🔄", skipped: "⏭️", missing: "❌" }[p.status] || "❓";
    const cls = p.status === "ok" ? "" : (p.status === "adaptable" ? "warn" : "muted");
    let note = escapeHtml(p.action || "");
    if (p.windows_hits && p.windows_hits.length) note += " <span class='muted'>[Windows API: " + escapeHtml(p.windows_hits.slice(0, 3).join(", ")) + "]</span>";
    if (p.has_variant) note += " <span class='muted'>[有平台变体]</span>";
    return "<tr><td>" + icon + " " + escapeHtml(p.id) + "</td><td class='" + cls + "'>" + icon + " " +
      ({ ok: "原生兼容", adaptable: "可适配", skipped: "降级跳过", missing: "缺失" }[p.status] || p.status) +
      "</td><td>" + note + "</td></tr>";
  }).join("");
  $("#adaptBody").innerHTML = rows || "<tr><td colspan='3' class='muted'>无插件数据</td></tr>";
}

function renderAdaptStatus(st, checkData) {
  const hasAdaptable = (checkData.stats || {}).adaptable > 0;
  const actionPanel = $("#adaptActionPanel");
  const progressPanel = $("#adaptProgressPanel");
  const resultPanel = $("#adaptResultPanel");

  if (st.running) {
    adaptRunning = true;
    actionPanel.style.display = "none";
    progressPanel.style.display = "block";
    resultPanel.style.display = "none";
    $("#adaptProgressBar").style.width = "40%";
    startAdaptPolling();
    return;
  }
  // 未运行：显示确认按钮（有可适配插件时）
  if (hasAdaptable && !st.running) {
    const need = (checkData.stats || {}).adaptable || 0;
    const skip = (checkData.stats || {}).skipped || 0;
    actionPanel.style.display = "block";
    $("#adaptActionText").innerHTML =
      "检测到当前系统（" + escapeHtml(checkData.platform_name || "") + "）有 <b style='color:#e65100'>" + need +
      "</b> 个插件需要适配、<b>" + skip + "</b> 个插件将降级跳过。<br>" +
      "点击下方按钮，7Tan 将自动完成全部操作：复制平台插件 → 安装依赖 → 自测 → 启用，通常 1~3 分钟。";
  } else {
    actionPanel.style.display = "none";
  }
  // 历史报告（适配完成过）
  if (st.has_report && st.report && st.report.adapted_at) {
    resultPanel.style.display = "block";
    const r = st.report;
    const s = r.stats || {};
    $("#adaptResult").innerHTML =
      "<div>上次适配：<b>" + escapeHtml(r.adapted_at || "") + "</b>（" + escapeHtml(r.platform_name || "") + "）</div>" +
      "<div>✅ 原生兼容 <b>" + (s.ok || 0) + "</b> · 🔄 已适配 <b style='color:#2e7d32'>" + (s.adapted || 0) + "</b> · ⏭️ 跳过 <b>" + (s.skipped || 0) + "</b> · ❌ 失败 <b style='color:#c62828'>" + (s.failed || 0) + "</b></div>";
  } else if (!hasAdaptable) {
    resultPanel.style.display = "block";
    $("#adaptResult").innerHTML = "<div class='muted'>✅ 当前系统所有插件均可直接使用，无需适配。</div>";
  }
}

function startAdaptPolling() {
  if (adaptTimer) return;
  adaptTimer = setInterval(async () => {
    try {
      const st = await API.req("GET", "/api/adapt/status");
      const log = st.log_tail || "";
      if (log) $("#adaptLog").textContent = log;
      $("#adaptProgressBar").style.width = "65%";
      if (!st.running) {
        clearInterval(adaptTimer); adaptTimer = null;
        adaptRunning = false;
        $("#adaptProgressBar").style.width = "100%";
        // 完成：重新体检 + 显示报告
        const data = await API.req("GET", "/api/adapt/check");
        renderAdaptSystem(data);
        renderAdaptPlugins(data.plugins || []);
        renderAdaptStatus(st, data);
        toast("✅ 平台适配完成");
      }
    } catch (e) { /* 忽略轮询瞬时错误 */ }
  }, 1500);
}

$("#adaptRunBtn").addEventListener("click", async () => {
  $("#adaptRunBtn").disabled = true;
  $("#adaptRunBtn").textContent = "⏳ 正在启动适配…";
  try {
    const r = await API.req("POST", "/api/adapt/run");
    if (!r.ok) { toast(r.msg || "启动失败", true); $("#adaptRunBtn").disabled = false; $("#adaptRunBtn").textContent = "✅ 确认适配（一键完成）"; return; }
    toast("🚀 适配已启动，请稍候…");
    renderAdaptStatus({ running: true }, null);
  } catch (e) {
    toast("启动失败: " + e.message, true);
    $("#adaptRunBtn").disabled = false;
    $("#adaptRunBtn").textContent = "✅ 确认适配（一键完成）";
  }
});

$("#adaptRefreshBtn").addEventListener("click", () => loadAdaptView());

/* ===== 侧栏版本号动态同步 ===== */
(async () => {
  try {
    const d = await API.get("/api/update/check");
    if (d && d.current) {
      const el = document.getElementById("webVersion");
      if (el) el.textContent = "7tan.com V" + d.current;
    }
  } catch (e) { /* 保持 HTML 默认值 */ }
})();

/* ===== 平台自适应：Windows 下隐藏「平台适配」入口（该功能仅供其他系统包使用）===== */
(async () => {
  try {
    const d = await API.req("GET", "/api/adapt/check");
    const isWin = d && (d.platform === "win32" || String(d.platform_name || "").toLowerCase() === "windows");
    if (isWin) {
      const navBtn = document.querySelector('.nav-item[data-view="adapt"]');
      if (navBtn) navBtn.style.display = "none";
      if (currentView === "adapt") switchView("chat");
    }
  } catch (e) { /* 接口不可用时保持原样，不阻塞其它功能 */ }
})();

/* ===== API Key 显示/隐藏按钮：动态注入（兼容浏览器缓存旧 HTML 的场景） ===== */
function injectKeyVisibility() {
  ["aiKey", "visKey"].forEach((id) => {
    const inp = document.getElementById(id);
    if (!inp) return;
    if (inp.parentElement && inp.parentElement.querySelector("button")) return; // 新版 HTML 已自带按钮
    const wrap = document.createElement("div");
    wrap.style.cssText = "display:block;position:relative;margin-top:2px;";
    inp.parentNode.insertBefore(wrap, inp);
    wrap.appendChild(inp);
    inp.style.width = "100%"; inp.style.boxSizing = "border-box"; inp.style.paddingRight = "38px";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.innerHTML = keyEyeSvg(true);
    btn.title = "显示/隐藏";
    btn.style.cssText = "position:absolute;right:4px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;padding:4px;opacity:0.9;color:#f0f0f0;display:flex;align-items:center;";
    btn.onclick = () => toggleKeyVis(id, btn);
    wrap.appendChild(btn);
  });
}
injectKeyVisibility();
