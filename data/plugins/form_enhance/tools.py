"""
自动填表增强插件 — 智能识别和填写复杂表单
v2: 修复 contenteditable 标题框 bug（微信编辑器 div#title）
    新增 upload_to_page 文件上传工具（base64 注入 File API）
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="detect_form_fields",
    description="自动检测当前页面所有表单字段，返回字段名称、类型、是否必填等信息。用于在发布前了解所有需要填写的内容。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="publish",
    requires_browser=True,
)
def detect_form_fields() -> str:
    """检测当前页面所有表单字段"""
    from src.tools.browser_bridge import get_bridge
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未就绪"

    js = """
    (function() {
        var result = {forms: 0, fields: []};
        function collectFrom(doc, prefix) {
            var inputs = doc.querySelectorAll('input, textarea, select, [contenteditable="true"]');
            inputs.forEach(function(el, i) {
                var field = {
                    tag: el.tagName.toLowerCase(),
                    name: el.name || el.id || (prefix + 'field_' + i),
                    type: el.type || 'text',
                    placeholder: el.placeholder || '',
                    required: el.required || el.hasAttribute('required'),
                    visible: el.offsetParent !== null,
                    value: el.value || el.textContent || ''
                };
                if (el.isContentEditable) field.tag = 'richtext';
                result.fields.push(field);
            });
            var frames = doc.querySelectorAll('iframe');
            for (var j = 0; j < frames.length; j++) {
                try {
                    var fd = frames[j].contentDocument;
                    if (fd) collectFrom(fd, prefix + 'iframe' + j + '_');
                } catch(e) {}
            }
        }
        collectFrom(document, '');
        return JSON.stringify(result);
    })()
    """
    result = bridge.execute_js(js, timeout=4.0)
    try:
        import json
        data = json.loads(result)
        fields = data.get("fields", [])

        output = f"📋 检测到 {len(fields)} 个字段:\n\n"
        for f in fields:
            icon = "⚠️" if f.get("required") else "  "
            vis = "👁" if f.get("visible") else "🙈"
            output += f"{icon}{vis} [{f['tag']}] {f['name']}"
            if f.get("placeholder"):
                output += f" (提示: {f['placeholder'][:30]})"
            if f.get("value"):
                output += f" = {f['value'][:40]}"
            output += "\n"
        return output
    except Exception as e:
        return f"❌ 表单检测失败: {e}\n原始: {result[:200]}"


@register_tool(
    name="fill_all_fields",
    description="批量填写表单所有字段。自动映射内容到正确的表单输入框。用于一次性填完发布表单的所有内容。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "游戏标题"},
            "intro": {"type": "string", "description": "游戏简介/正文(支持HTML)"},
            "download_url": {"type": "string", "description": "下载链接"},
            "category": {"type": "string", "description": "分类"},
            "tags": {"type": "string", "description": "标签（逗号分隔）"},
        },
        "required": ["title", "intro", "download_url"]
    },
    category="publish",
    requires_browser=True,
)
def fill_all_fields(title: str, intro: str, download_url: str,
                    category: str = "", tags: str = "") -> str:
    """批量填写所有表单字段（v2: 支持 contenteditable 标题框 + iframe 正文）"""
    from src.tools.browser_bridge import get_bridge
    import json
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未就绪"

    results = []
    esc_title = json.dumps(title)
    esc_intro = json.dumps(intro)
    esc_url = json.dumps(download_url)
    esc_cat = json.dumps(category)
    esc_tags = json.dumps(tags)

    # 通用填表脚本 — 按字段特征智能匹配（含 iframe 与 contenteditable 支持）
    js = f"""
    (function() {{
        var results = [];

        function findInFrames(sel) {{
            var el = document.querySelector(sel);
            if (el) return el;
            var frames = document.querySelectorAll('iframe');
            for (var i = 0; i < frames.length; i++) {{
                try {{
                    var d = frames[i].contentDocument;
                    if (!d) continue;
                    el = d.querySelector(sel);
                    if (el) return el;
                }} catch(e) {{}}
            }}
            return null;
        }}

        // React 受控 input/textarea：native setter + input 事件
        function setNativeValue(el, value) {{
            try {{
                var proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                setter.call(el, value);
            }} catch(e) {{
                el.value = value;
            }}
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
        }}

        // contenteditable（React/ProseMirror）：模拟真实输入
        function setContentEditable(el, value, isHtml) {{
            el.focus();
            try {{
                var sel = window.getSelection();
                sel.selectAllChildren(el);
                document.execCommand('delete');
                if (isHtml) {{
                    document.execCommand('insertHTML', false, value);
                }} else {{
                    document.execCommand('insertText', false, value);
                }}
            }} catch(e) {{
                el.innerHTML = isHtml ? value : value.replace(/</g, '&lt;');
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        }}

        function fill(el, value, isHtml) {{
            if (el.isContentEditable || (el.tagName === 'DIV' && el.getAttribute('contenteditable'))) {{
                setContentEditable(el, value, !!isHtml);
            }} else {{
                setNativeValue(el, value);
            }}
        }}

        var fields = [
            {{selectors: ['[placeholder*="标题"]', 'textarea#title', 'input#title', 'div#title', '#title'], value: {esc_title}, name: '标题'}},
            {{selectors: ['[placeholder*="正文"]', '[data-placeholder*="正文"]', '#js_editor .ProseMirror', '.editor-content .ProseMirror', 'div[contenteditable="true"]:not(#title):not([class*="title"])', '.ProseMirror:not(#title):not([class*="title"])'], value: {esc_intro}, name: '简介', is_html: true}},
            {{selectors: ['input[name="source_url"]', 'input[name="download_url"]', 'input[name="download"]', '#download_url', 'input[placeholder*="原文链接"]', 'input[placeholder*="下载"]'], value: {esc_url}, name: '原文链接'}},
            {{selectors: ['select[name="category"]', '#category', 'select[name="type"]'], value: {esc_cat}, name: '分类', is_select: true}},
            {{selectors: ['input[name="tags"]', '#tags', 'input[placeholder*="标签"]'], value: {esc_tags}, name: '标签'}},
        ];

        fields.forEach(function(f) {{
            var filled = false;
            f.selectors.forEach(function(sel) {{
                if (filled) return;
                var el = findInFrames(sel);
                if (!el) return;
                if (f.is_html && !el.isContentEditable && el.tagName !== 'DIV') {{
                    // textarea: 直接赋值 HTML 源码
                    el.value = f.value;
                }} else {{
                    fill(el, f.value, f.is_html);
                }}
                filled = true;
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                results.push('✅ ' + f.name + ': ' + sel);
            }});
            if (!filled && f.value) {{
                results.push('❌ ' + f.name + ': 未找到匹配字段');
            }}
        }});

        return JSON.stringify(results);
    }})()
    """
    result = bridge.execute_js(js, timeout=6.0)
    try:
        data = json.loads(result)
        return "📝 批量填表结果:\n" + "\n".join(data)
    except Exception:
        return f"📝 填表已执行: {result[:800]}"


@register_tool(
    name="upload_to_page",
    description="上传本地文件到当前页面的文件输入框（如公众号封面、图片上传）。通过 base64 注入 File API，无需文件对话框。",
    parameters={
        "type": "object",
        "properties": {
            "local_path": {"type": "string", "description": "本地文件路径"},
            "selector": {"type": "string", "description": "CSS 选择器（可留空自动尝试常见候选）"},
        },
        "required": ["local_path"]
    },
    category="publish",
    requires_browser=True,
)
def upload_to_page(local_path: str, selector: str = "") -> str:
    """上传文件到页面 input[type=file]"""
    from src.tools.browser_bridge import get_bridge
    import os
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未就绪"
    if not os.path.exists(local_path):
        return f"❌ 本地文件不存在: {local_path}"

    candidates = []
    if selector:
        candidates = [s.strip() for s in selector.split(",") if s.strip()]
    else:
        candidates = [
            '[class*="cover"] input[type="file"]',
            '#js_cover_input',
            '.weui-desktop-uploader__input',
            '.js_cover_upload input[type="file"]',
            'input[type="file"][accept*="image"]',
            '.weui-desktop-form__upload input[type="file"]',
            'input[type="file"]',
        ]

    tried = []
    for sel in candidates:
        tried.append(sel)
        try:
            res = bridge.upload_files(sel, [local_path])
        except Exception as e:
            return f"❌ 上传异常: {e}"
        if res == "selector_not_found":
            continue
        if res == "no_valid_files":
            return "❌ 没有有效文件"
        return f"✅ 上传成功 ({res}) → 选择器: {sel}"

    return f"❌ 未找到可用文件输入框，尝试过: {', '.join(tried)}"
