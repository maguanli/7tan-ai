"""
自动填表增强插件 — 智能识别和填写复杂表单
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
        var forms = document.querySelectorAll('form');
        if (!forms.length) return JSON.stringify({forms: 0, fields: []});

        var result = {forms: forms.length, fields: []};
        forms.forEach(function(form, fi) {
            var inputs = form.querySelectorAll('input, textarea, select, [contenteditable="true"]');
            inputs.forEach(function(el, i) {
                var field = {
                    form: fi,
                    tag: el.tagName.toLowerCase(),
                    name: el.name || el.id || ('field_' + i),
                    type: el.type || 'text',
                    placeholder: el.placeholder || '',
                    required: el.required || el.hasAttribute('required'),
                    visible: el.offsetParent !== null,
                    value: el.value || el.textContent || ''
                };
                if (el.isContentEditable) field.tag = 'richtext';
                result.fields.push(field);
            });
        });
        return JSON.stringify(result);
    })()
    """
    result = bridge.execute_js(js, timeout=4.0)
    try:
        import json
        data = json.loads(result)
        forms = data.get("forms", 0)
        fields = data.get("fields", [])

        output = f"📋 检测到 {forms} 个表单, {len(fields)} 个字段:\n\n"
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
            "intro": {"type": "string", "description": "游戏简介/正文"},
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
    """批量填写所有表单字段"""
    from src.tools.browser_bridge import get_bridge
    import json
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未就绪"

    results = []
    escaped_intro = json.dumps(intro)

    # 通用填表脚本 — 按字段特征智能匹配
    js = f"""
    (function() {{
        var results = [];
        var fields = [
            {{selectors: ['input[name="title"]', '#title', 'input[placeholder*="标题"]'], value: {json.dumps(title)}, name: '标题'}},
            {{selectors: ['textarea[name="content"]', 'textarea[name="intro"]', '#content', '.editor textarea', '[contenteditable="true"]'], value: {escaped_intro}, name: '简介', is_html: true}},
            {{selectors: ['input[name="download_url"]', 'input[name="download"]', '#download_url', 'input[placeholder*="下载"]'], value: '{download_url}', name: '下载链接'}},
            {{selectors: ['select[name="category"]', '#category', 'select[name="type"]'], value: '{category}', name: '分类', is_select: true}},
            {{selectors: ['input[name="tags"]', '#tags', 'input[placeholder*="标签"]'], value: '{tags}', name: '标签'}},
        ];

        fields.forEach(function(f) {{
            var filled = false;
            f.selectors.forEach(function(sel) {{
                if (filled) return;
                var el = document.querySelector(sel);
                if (!el) return;

                if (f.is_html && el.isContentEditable) {{
                    el.innerHTML = f.value;
                    filled = true;
                }} else if (f.is_select) {{
                    var opts = el.options;
                    for (var i = 0; i < opts.length; i++) {{
                        if (opts[i].text.includes(f.value) || opts[i].value.includes(f.value)) {{
                            el.value = opts[i].value;
                            filled = true;
                            break;
                        }}
                    }}
                    if (!filled && f.value) {{
                        el.value = f.value;
                        filled = true;
                    }}
                }} else if (!f.is_html) {{
                    el.value = f.value;
                    filled = true;
                }}

                if (filled) {{
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    results.push('✅ ' + f.name + ': ' + sel);
                }}
            }});
            if (!filled && f.value) {{
                results.push('❌ ' + f.name + ': 未找到匹配字段');
            }}
        }});

        return JSON.stringify(results);
    }})()
    """
    result = bridge.execute_js(js, timeout=5.0)
    try:
        data = json.loads(result)
        return "📝 批量填表结果:\n" + "\n".join(data)
    except Exception:
        return f"📝 填表已执行: {result[:800]}"
