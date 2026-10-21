/* WebMirror 前端逻辑 */
const $ = (id) => document.getElementById(id);
const state = { tasks: [], cur: null, es: null, seq: 0, tree: null, selFile: null };

/* ---------------- 通用 ---------------- */
function toast(msg, ms = 2200) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._tm);
  t._tm = setTimeout(() => t.classList.remove('show'), ms);
}
async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}
const fmtSize = (n) => {
  n = n || 0;
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  if (n < 1024 ** 3) return (n / 1024 / 1024).toFixed(2) + ' MB';
  return (n / 1024 ** 3).toFixed(2) + ' GB';
};
const statusText = { pending: '排队中', running: '抓取中', done: '已完成',
  error: '出错', cancelled: '已停止', interrupted: '已中断' };

/* ---------------- 表单 ---------------- */
function collectParams() {
  return {
    url: $('url').value.trim(),
    max_depth: +$('max_depth').value || 0,
    max_pages: +$('max_pages').value || 300,
    concurrency: +$('concurrency').value || 8,
    delay: +$('delay').value || 0,
    same_domain: $('same_domain').checked,
    asset_scope: $('asset_scope').value,
    include_assets: $('include_assets').checked,
    rewrite_links: $('rewrite_links').checked,
    with_host_dir: $('with_host_dir').checked,
    obey_robots: $('obey_robots').checked,
    param_mode: $('param_mode').value,
    extensionless: $('extensionless').value,
  };
}

$('crawl-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const p = collectParams();
  if (!p.url) return toast('请先填写起始网址');
  $('btn-start').disabled = true;
  try {
    const r = await api('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(p),
    });
    toast(`已启动 ${r.count} 个镜像任务`);
    await loadTasks();
    if (r.tasks && r.tasks.length) selectTask(r.tasks[0].id);
  } catch (err) {
    toast('启动失败：' + err.message);
  } finally {
    $('btn-start').disabled = false;
  }
});

$('btn-preview-path').addEventListener('click', async () => {
  const url = $('url').value.trim().split('\n')[0].trim();
  if (!url) return toast('请先填写网址');
  try {
    const r = await api('/api/pathpreview?' + new URLSearchParams({
      url, param_mode: $('param_mode').value,
      extensionless: $('extensionless').value,
      with_host: $('with_host_dir').checked,
    }));
    $('path-preview-out').textContent = '📁 ' + r.relpath;
  } catch (err) {
    $('path-preview-out').textContent = '❌ ' + err.message;
  }
});

/* ---------------- 任务列表 ---------------- */
async function loadTasks() {
  const r = await api('/api/tasks');
  state.tasks = r.tasks;
  renderTasks();
  return r.tasks;
}

function renderTasks() {
  const box = $('task-list');
  if (!state.tasks.length) {
    box.innerHTML = '<div class="muted" style="padding:6px 4px">还没有任务</div>';
    return;
  }
  box.innerHTML = state.tasks.map((t) => {
    const host = (t.start_url || '').replace(/^https?:\/\//, '').slice(0, 40);
    const st = t.stats || {};
    const sp = t.status === 'running' ? ` · ${(st.speed_recent != null ? st.speed_recent : 0)}/s` : '';
    const sub = `${statusText[t.status] || t.status} · 页面 ${st.pages_ok || 0} · 文件 ${st.files || 0}${sp}`;
    return `<div class="task-item ${state.cur === t.id ? 'active' : ''}" data-id="${t.id}">
      <div class="t1">
        <span class="host">${esc(host)}</span>
        <span class="badge ${t.status}">${statusText[t.status] || t.status}</span>
      </div>
      <div class="sub">${esc(sub)}</div>
    </div>`;
  }).join('');
  box.querySelectorAll('.task-item').forEach((el) => {
    el.addEventListener('click', () => selectTask(el.dataset.id));
  });
}

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function selectTask(id) {
  if (state.es) { state.es.close(); state.es = null; }
  state.cur = id;
  state.seq = 0;
  state.tree = null;
  $('log-box').textContent = '';
  $('preview').textContent = '点击左侧文件查看内容';
  $('preview-title').textContent = '预览';
  renderTasks();
  const t = state.tasks.find((x) => x.id === id);
  if (t) applyTask(t);
  connectSSE(id);
  loadTree(id);
}

function applyTask(t) {
  const st = t.stats || {};
  $('cur-title').textContent = (t.start_url || '').replace(/^https?:\/\//, '').slice(0, 70) || '任务';
  $('cur-url').textContent = `ID ${t.id} · 输出 ${t.out_root || ''}`;
  const bd = $('cur-status');
  bd.textContent = statusText[t.status] || t.status;
  bd.className = 'badge ' + t.status;

  $('m-pages').textContent = st.pages_ok || 0;
  $('m-assets').textContent = st.assets_ok || 0;
  $('m-files').textContent = st.files || 0;
  $('m-queue').textContent = st.queue_size || 0;
  $('m-size').textContent = fmtSize(st.bytes);
  $('m-speed-recent').textContent = (st.speed_recent != null ? st.speed_recent : 0);
  $('m-speed').textContent = st.speed || 0;
  $('m-time').textContent = (st.elapsed || 0) + 's';
  $('m-err').textContent = (st.pages_fail || 0) + (st.assets_fail || 0);

  const total = (st.pages_total || 0) + (st.assets_total || 0);
  const done = (st.pages_ok || 0) + (st.assets_ok || 0) +
    (st.pages_fail || 0) + (st.assets_fail || 0);
  let pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  if (t.status === 'done') pct = 100;
  $('bar-fill').style.width = pct + '%';
}

/* ---------------- SSE 实时流 ---------------- */
function connectSSE(id) {
  const es = new EventSource(`/api/tasks/${id}/events`);
  state.es = es;
  es.onmessage = (ev) => {
    let d;
    try { d = JSON.parse(ev.data); } catch { return; }
    if (d.type === 'end') {
      es.close(); state.es = null;
      loadTasks();
      if (state.cur === id) loadTree(id);
      return;
    }
    if (d.task && state.cur === id) applyTask(d.task);
    if (d.logs && d.logs.length && state.cur === id) appendLogs(d.logs);
    if (d.task) {
      const idx = state.tasks.findIndex((x) => x.id === d.task.id);
      if (idx >= 0) { state.tasks[idx] = d.task; renderTasks(); }
    }
  };
  es.onerror = () => { es.close(); state.es = null; };
}

function appendLogs(logs) {
  const box = $('log-box');
  const frag = document.createDocumentFragment();
  logs.forEach((l) => {
    const div = document.createElement('div');
    div.className = 'lg-' + (l.level || 'info');
    div.textContent = `[${l.t}] ${l.msg}`;
    frag.appendChild(div);
  });
  box.appendChild(frag);
  if (box.childNodes.length > 1200) {
    for (let i = 0; i < 300; i++) box.removeChild(box.firstChild);
  }
  if ($('auto-scroll').checked) box.scrollTop = box.scrollHeight;
}

/* ---------------- 操作按钮 ---------------- */
$('btn-cancel').addEventListener('click', async () => {
  if (!state.cur) return toast('请先选择任务');
  await api(`/api/tasks/${state.cur}/cancel`, { method: 'POST' });
  toast('已发送停止指令');
});
$('btn-zip').addEventListener('click', () => {
  if (!state.cur) return toast('请先选择任务');
  const t = state.tasks.find((x) => x.id === state.cur);
  if (t && t.status === 'running') return toast('任务运行中，完成后才能打包');
  window.location.href = `/api/tasks/${state.cur}/download`;
});
$('btn-del').addEventListener('click', async () => {
  if (!state.cur) return toast('请先选择任务');
  if (!confirm('删除该任务及其已下载的文件？此操作不可恢复。')) return;
  await api(`/api/tasks/${state.cur}/delete`, { method: 'POST' });
  state.cur = null;
  $('tree').textContent = '暂无文件';
  toast('任务已删除');
  loadTasks();
});
$('btn-refresh').addEventListener('click', () => { loadTasks(); toast('已刷新'); });
$('btn-tree').addEventListener('click', () => state.cur && loadTree(state.cur));

/* ---------------- 文件树 ---------------- */
async function loadTree(id) {
  try {
    const r = await api(`/api/tasks/${id}/tree`);
    state.tree = r.tree;
    $('tree-size').textContent = `(${fmtSize(r.size)})`;
    renderTree(r.tree);
  } catch { /* ignore */ }
}

function renderTree(node) {
  const box = $('tree');
  box.innerHTML = '';
  if (!node || !node.children || !node.children.length) {
    box.textContent = '暂无文件';
    return;
  }
  const build = (n, depth) => {
    const wrap = document.createElement('div');
    (n.children || []).forEach((c) => {
      const row = document.createElement('div');
      row.className = 'tnode ' + c.type;
      row.innerHTML = `<span class="ic">${c.type === 'dir' ? '📁' : iconFor(c.name)}</span>
        <span class="nm">${esc(c.name)}</span>
        <span class="sz">${c.type === 'file' ? fmtSize(c.size) : ''}</span>`;
      wrap.appendChild(row);
      if (c.type === 'dir') {
        const kids = build(c, depth + 1);
        kids.className = 'tchildren';
        kids.style.display = depth >= 1 ? 'none' : 'block';
        wrap.appendChild(kids);
        row.addEventListener('click', (e) => {
          e.stopPropagation();
          row.querySelector('.ic').textContent = kids.style.display === 'none' ? '📂' : '📁';
          kids.style.display = kids.style.display === 'none' ? 'block' : 'none';
        });
      } else {
        row.addEventListener('click', () => {
          box.querySelectorAll('.tnode.file.active').forEach((x) => x.classList.remove('active'));
          row.classList.add('active');
          previewFile(c.path, c.name);
        });
      }
    });
    return wrap;
  };
  box.appendChild(build(node, 0));
}

function iconFor(name) {
  const ext = (name.split('.').pop() || '').toLowerCase();
  if (['html', 'htm'].includes(ext)) return '🌐';
  if (ext === 'css') return '🎨';
  if (ext === 'js') return '📜';
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ico', 'avif'].includes(ext)) return '🖼';
  if (ext === 'json') return '🧾';
  if (['woff', 'woff2', 'ttf', 'otf'].includes(ext)) return '🔤';
  if (['mp4', 'webm', 'mp3'].includes(ext)) return '🎬';
  return '📄';
}

/* ---------------- 文件预览 ---------------- */
async function previewFile(path, name) {
  const id = state.cur;
  $('preview-title').textContent = name;
  const ext = (path.split('.').pop() || '').toLowerCase();
  const box = $('preview');
  const isImg = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ico', 'avif', 'bmp'].includes(ext);
  const isHtml = ['html', 'htm'].includes(ext);
  // 预览用「保持原路径」的镜像地址，页面内相对引用的 CSS/JS/图片才能正确加载
  const mirrorUrl = `/mirror/${id}/` + path.split('/').map(encodeURIComponent).join('/');
  const rawUrl = `/api/tasks/${id}/serve?path=${encodeURIComponent(path)}`;

  if (isImg) {
    box.innerHTML = `<img src="${mirrorUrl}" alt="${esc(name)}">`;
    $('preview-meta').textContent = '图片 · 原样保存';
    return;
  }
  if (isHtml) {
    box.innerHTML = `
      <div style="margin-bottom:8px">
        <a href="${mirrorUrl}" target="_blank" style="color:#7fb0ff">🔗 新窗口打开镜像页面</a>
      </div>
      <iframe src="${mirrorUrl}"></iframe>`;
    $('preview-meta').textContent = 'HTML（本地镜像渲染）';
    return;
  }
  try {
    const r = await api(`/api/tasks/${id}/raw?path=${encodeURIComponent(path)}&as_text=true`);
    box.textContent = r.text || '(空文件)';
    $('preview-meta').textContent = fmtSize(r.size);
  } catch (err) {
    box.textContent = '无法预览：' + err.message;
  }
}

/* ---------------- 启动 ---------------- */
loadTasks().then(() => {
  const running = state.tasks.find((t) => t.status === 'running');
  if (running) selectTask(running.id);
  else if (state.tasks.length) selectTask(state.tasks[0].id);
});
setInterval(() => { if (!state.cur) loadTasks(); }, 10000);
