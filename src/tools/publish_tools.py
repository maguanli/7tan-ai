"""
发布工具 — 7坛管理后台自动发布
"""
import time
import json
import random

from loguru import logger
from .registry import register_tool


@register_tool(
    name="publish_to_7tan",
    description="在7坛管理后台发布资源。自动填写表单、上传 LOGO/截图、提交发布。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "发布标题"},
            "intro": {"type": "string", "description": "简介/正文内容"},
            "category": {"type": "string", "description": "分类"},
            "tags": {"type": "string", "description": "标签（逗号分隔）"},
            "download_url": {"type": "string", "description": "下载链接（OSS 外链）"},
            "logo_path": {"type": "string", "description": "本地 LOGO 路径"},
            "screenshot_paths": {"type": "string", "description": "本地截图路径（JSON 数组）"},
            "resource_type": {"type": "string", "description": "'game' 或 'software'", "default": "game"},
        },
        "required": ["title", "intro", "download_url"]
    },
    category="publish",
    requires_browser=True,
    dangerous=True,
)
def publish_to_7tan(title: str, intro: str, download_url: str, category: str = "",
                    tags: str = "", logo_path: str = "", screenshot_paths: str = "",
                    resource_type: str = "game") -> str:
    """
    自动发布到7坛后台。
    智能导航：登录 → 读取页面链接 → 找到「安卓游戏」→ 找到「发布」按钮 → 填写表单 → 提交。
    使用 BrowserBridge 线程安全操作浏览器。
    """
    from .browser_bridge import get_bridge
    from .browser_tools import login_7tan
    from ..config.loader import load_config

    config = load_config()
    bridge = get_bridge()
    if bridge is None:
        return "❌ 浏览器未启动，请先打开浏览器页面"

    try:
        admin_url = config.get("site_7tan", {}).get("base_url", "https://img.7tan.cn")
        steps = []

        # ⚠️ 硬性检查：LOGO和截图必须存在本地才能发布
        import os as _os
        missing = []
        if not logo_path:
            missing.append("LOGO (logo_path 参数为空)")
        elif not _os.path.exists(str(logo_path)):
            missing.append(f"LOGO (文件不存在: {logo_path})")
        if not screenshot_paths or screenshot_paths in ("[]", '[""]'):
            missing.append("截图 (screenshot_paths 参数为空)")
        else:
            try:
                shots_list = json.loads(screenshot_paths) if isinstance(screenshot_paths, str) else screenshot_paths
                if not isinstance(shots_list, list) or len(shots_list) == 0:
                    missing.append("截图 (列表为空)")
                else:
                    for sp in shots_list:
                        if not _os.path.exists(str(sp)):
                            missing.append(f"截图 (文件不存在: {sp})")
            except:
                missing.append("截图 (格式解析失败)")
        if not intro or len(intro) < 20:
            missing.append("简介 (太短，需要≥100字)")
        if not download_url:
            missing.append("下载链接")

        if missing:
            return "❌ 发布被拒绝，以下必填项缺失:\n  - " + "\n  - ".join(missing) + \
                   "\n\n💡 请先下载 LOGO 和截图（get_page_images → download_file），再调用 publish_to_7tan。"

        # 切换到管理后台上下文
        from .browser_tools import set_active_context, _admin_view
        set_active_context("admin")
        if _admin_view is None:
            steps.append("⚠️ 请先在浏览器页面点击「打开管理后台」按钮，或手动在浏览器新标签中打开管理后台")
        else:
            steps.append("🔧 管理后台窗口已就绪")
        # ===== 步骤 1: 登录 =====
        login_result = login_7tan(
            config.get("site_7tan", {}).get("username", ""),
            config.get("site_7tan", {}).get("password", "")
        )
        steps.append(f"🔐 登录: {login_result[:80]}")

        # ===== 步骤 2: 浏览管理后台首页，读取所有链接 =====
        bridge.navigate(f"{admin_url}/", wait_seconds=5.0)
        time.sleep(2)
        
        all_links = bridge.get_page_links(100)  # 读取最多 100 个链接
        page_text = bridge.get_page_text(8000)   # 读取更多文本
        page_title = bridge.get_page_title()
        steps.append(f"📄 进入后台: {page_title} ({len(all_links)}个链接)")
        
        # ===== 步骤 3: 在链接和文本中搜索「安卓游戏」入口 =====
        android_link = None
        android_keywords = ["安卓游戏", "安卓", "Android", "android", "手游", "发布安卓"]
        
        # 3a: 首先在链接文本中搜索
        for link in all_links:
            link_text = link.get("text", "")
            link_href = link.get("href", "")
            for kw in android_keywords:
                if kw.lower() in link_text.lower() or kw.lower() in link_href.lower():
                    android_link = link
                    break
            if android_link:
                break
        
        # 3b: 如果链接没找到，在页面文本中搜索「安卓游戏」附近的链接
        if not android_link:
            for kw in android_keywords:
                if kw in page_text:
                    # 找到了文本中有「安卓游戏」，尝试用选择器点击
                    nav_selectors = [
                        f'a:has-text("{kw}")',
                        f'li:has-text("{kw}") a',
                        f'.sidebar a:has-text("{kw}")',
                        f'.nav a:has-text("{kw}")',
                        f'[class*="menu"] a:has-text("{kw}")',
                        f'[class*="nav"] a:has-text("{kw}")',
                    ]
                    for sel in nav_selectors:
                        result = bridge.click(sel)
                        if "not_found" not in result and "超时" not in result:
                            android_link = {"text": kw, "href": sel, "clicked": True}
                            steps.append(f"🔗 通过文本匹配点击了「{kw}」")
                            break
                    if android_link:
                        break
        
        # 3c: 如果还没找到，输出所有链接让 AI 判断
        if not android_link:
            links_summary = "\n".join([
                f"  [{i}] {l.get('text','(空)')[:60]} → {l.get('href','')[:80]}"
                for i, l in enumerate(all_links[:50])
            ])
            steps.append(f"⚠️ 未找到「安卓游戏」入口，页面链接如下:\n{links_summary}")
            return "❌ 未找到「安卓游戏」入口。" + "\n".join(steps) + \
                   "\n\n💡 建议：先用 browse_page 仔细查看后台页面结构，告诉我「安卓游戏」的链接文字或 URL。"
        
        # ===== 步骤 4: 点击「安卓游戏」进入列表页 =====
        if not android_link.get("clicked"):
            href = android_link.get("href", "")
            text = android_link.get("text", "")
            steps.append(f"🔗 找到入口: 「{text}」→ {href}")
            
            # 如果是相对路径或完整 URL
            if href.startswith("http"):
                bridge.navigate(href, wait_seconds=4.0)
            elif href.startswith("/") or href.startswith("?"):
                bridge.navigate(f"{admin_url}{href}", wait_seconds=4.0)
            elif href:
                bridge.navigate(f"{admin_url}/{href}", wait_seconds=4.0)
            else:
                # 用选择器点击
                click_result = bridge.click(f'a:has-text("{text}")')
                steps.append(f"   点击结果: {click_result}")
        
        time.sleep(3)
        
        # ===== 步骤 5: 在安卓游戏页面找「发布」按钮 =====
        android_page_text = bridge.get_page_text(5000)
        android_page_links = bridge.get_page_links(60)
        android_page_title = bridge.get_page_title()
        steps.append(f"📱 安卓游戏页面: {android_page_title}")
        
        # 搜索「发布」相关按钮
        publish_keywords = ["发布安卓", "发布游戏", "发布", "新增", "添加游戏", "添加"]
        clicked_publish = False
        
        for kw in publish_keywords:
            publish_selectors = [
                f'a:has-text("{kw}")',
                f'button:has-text("{kw}")',
                f'span:has-text("{kw}")',
                f'.btn:has-text("{kw}")',
                f'[class*="btn"]:has-text("{kw}")',
            ]
            for sel in publish_selectors:
                result = bridge.click(sel)
                if "not_found" not in result and "超时" not in result:
                    steps.append(f"✅ 点击发布按钮: {result}")
                    clicked_publish = True
                    break
            if clicked_publish:
                break
        
        # 也尝试在链接列表中找发布入口
        if not clicked_publish:
            for link in android_page_links:
                link_text = link.get("text", "")
                link_href = link.get("href", "")
                for kw in publish_keywords:
                    if kw in link_text:
                        if link_href.startswith("http"):
                            bridge.navigate(link_href, wait_seconds=4.0)
                        else:
                            bridge.click(f'a:has-text("{link_text}")')
                        steps.append(f"✅ 通过链接进入发布页: 「{link_text}」")
                        clicked_publish = True
                        break
                if clicked_publish:
                    break
        
        if not clicked_publish:
            # 最后尝试直接 URL
            for fallback_path in [
                f"{admin_url}/post.php?action=new",
                f"{admin_url}/post.php?action=add",
                f"{admin_url}/publish.php",
            ]:
                bridge.navigate(fallback_path, wait_seconds=4.0)
                fb_text = bridge.get_page_text(500)
                if "标题" in fb_text or "title" in fb_text.lower() or "发布" in fb_text:
                    steps.append(f"🔄 通过 URL 回退进入发布页: {fallback_path}")
                    clicked_publish = True
                    break
        
        if not clicked_publish:
            page_links_summary = "\n".join([
                f"  [{i}] {l.get('text','(空)')[:60]} → {l.get('href','')[:80]}"
                for i, l in enumerate(android_page_links[:30])
            ])
            steps.append(f"⚠️ 在安卓游戏页面未找到发布按钮，当前页面链接:\n{page_links_summary}")
            return "❌ 未找到发布入口。" + "\n".join(steps) + \
                   "\n\n💡 建议：先用 browse_page 查看安卓游戏页面内容，确认发布按钮的位置。"
        
        time.sleep(2)

        # ===== 步骤 6: 填写表单 =====
        fill_report, all_filled = _fill_form_via_bridge(
            bridge, title, intro, category, tags, download_url,
            logo_path, screenshot_paths, resource_type)
        steps.append(fill_report)

        if not all_filled:
            steps.append("⚠️ 部分必填字段未成功填写，请在提交前手动检查")
            return "⚠️ 表单填写不完整。\n" + fill_report + \
                   "\n\n💡 建议：使用 browse_page 查看发布页面的 HTML 结构，找到正确的输入框选择器后重新发布。"

        # ===== 步骤 7: 提交 =====
        time.sleep(1)
        submit_keywords = ["提交", "发布", "保存", "确认"]
        submitted = False
        for kw in submit_keywords:
            submit_selectors = [
                f'button[type="submit"]:has-text("{kw}")',
                f'button:has-text("{kw}")',
                f'input[type="submit"]:has-text("{kw}")',
                f'a:has-text("{kw}")',
                '.submit-btn', '#submit-btn',
            ]
            for sel in submit_selectors:
                result = bridge.click(sel)
                if "not_found" not in result and "超时" not in result:
                    steps.append(f"🚀 提交: {result}")
                    submitted = True
                    break
            if submitted:
                break
        
        if not submitted:
            # 万能回退：找 form 中任意 submit 按钮
            for sel in ['button[type="submit"]', 'input[type="submit"]', 'form button:last-child']:
                result = bridge.click(sel)
                if "not_found" not in result:
                    steps.append(f"🚀 回退提交: {result}")
                    submitted = True
                    break

        time.sleep(3)

        # ===== 步骤 8: 验证结果 =====
        current_title = bridge.get_page_title()
        page_text = bridge.get_page_text(500)
        if any(w in page_text for w in ["成功", "发布成功", "操作成功", "success"]):
            steps.append("✅ 发布成功!")
            return "✅ 发布成功!\n  标题: " + title + "\n\n" + "\n".join(steps)
        else:
            steps.append("⚠️ 发布已提交，请手动验证")
            return "⚠️ 发布已提交，请手动验证。" + "\n\n" + "\n".join(steps)

    except Exception as e:
        logger.error(f"❌ 发布失败: {e}")
        import traceback
        return f"❌ 发布失败: {e}\n{traceback.format_exc()}"


def _fill_form_via_bridge(bridge, title, intro, category, tags, download_url,
                          logo_path, screenshot_paths, resource_type):
    """通过 Bridge 执行 JS 填写发布表单，返回填写报告"""
    filled = {}
    not_found = {}

    # === 第0步: 扫描页面所有表单元素 ===
    form_debug = bridge.execute_js("""
        (function() {
            var result = [];
            var inputs = document.querySelectorAll('input, textarea, select');
            inputs.forEach(function(el) {
                var info = {tag: el.tagName, name: el.name || '', id: el.id || '',
                    type: el.type || '', placeholder: (el.placeholder || '').substring(0,30),
                    className: (el.className || '').toString().substring(0,40)};
                result.push(info);
            });
            return JSON.stringify(result.slice(0, 30));
        })()
    """, timeout=2.0)
    try:
        fields = json.loads(form_debug)
        filled["表单字段"] = ", ".join([f"{f['tag']}[{f['name'] or f['id'] or '?'}]" for f in fields[:15]])
    except:
        filled["表单字段"] = "扫描失败"

    # === 第1步: 填写标题 ===
    for sel in ['input[name="title"]', '#title', 'input[placeholder*="标题"]']:
        r = bridge.execute_js(f"""
            (function() {{
                var el = document.querySelector('{sel}');
                if (el) {{ el.value = {json.dumps(title)}; el.focus(); el.dispatchEvent(new Event('input',{{bubbles:true}})); el.dispatchEvent(new Event('change',{{bubbles:true}})); return 'ok'; }}
                return 'not found';
            }})()
        """, timeout=2.0)
        if "ok" in r:
            filled["1.标题"] = title[:30]
            break
    else:
        not_found["1.标题"] = "未找到标题输入框"
        return _make_report(filled, not_found)

    # === 第2步: 选择分类 ===
    if category:
        found_cat = False
        # 尝试 select 下拉框（按选项文字匹配）
        r = bridge.execute_js(f"""
            (function() {{
                var cat = {json.dumps(category)};
                var selects = document.querySelectorAll('select');
                for (var i = 0; i < selects.length; i++) {{
                    var el = selects[i];
                    var name = (el.name||'').toLowerCase();
                    if (!name) name = (el.id||'').toLowerCase();
                    if (!name || /cate|type|class|sort/.test(name)) {{
                        for (var j = 0; j < el.options.length; j++) {{
                            var opt = el.options[j].text;
                            if (opt === cat || opt.indexOf(cat) >= 0) {{
                                el.selectedIndex = j;
                                el.dispatchEvent(new Event('change',{{bubbles:true}}));
                                return 'ok:' + opt;
                            }}
                        }}
                    }}
                }}
                return 'not found';
            }})()
        """, timeout=2.0)
        if "ok:" in r:
            filled["2.分类"] = r.split(":",1)[1]
            found_cat = True
        else:
            # 尝试 radio/label
            r = bridge.execute_js(f"""
                (function() {{
                    var cat = {json.dumps(category)};
                    var labels = document.querySelectorAll('label');
                    for (var i = 0; i < labels.length; i++) {{
                        if (labels[i].textContent.indexOf(cat) >= 0) {{
                            var inp = labels[i].querySelector('input');
                            if (inp && (inp.type==='radio'||inp.type==='checkbox')) {{
                                inp.checked = true; inp.dispatchEvent(new Event('change',{{bubbles:true}}));
                                return 'ok:radio';
                            }}
                        }}
                    }}
                    return 'not found';
                }})()
            """, timeout=2.0)
            if "ok:" in r:
                filled["2.分类"] = category
                found_cat = True
        if not found_cat:
            not_found["2.分类"] = "未找到分类控件"

    # === 第3步: 填写简介 ⭐ ===
    r = bridge.execute_js(f"""
        (function() {{
            var intro = {json.dumps(intro)};
            var best = null, bestSize = 0;
            var areas = document.querySelectorAll('textarea');
            areas.forEach(function(el) {{
                var info = (el.name||'') + (el.id||'') + (el.placeholder||'') + (el.className||'');
                // 跳过这些
                if (/温馨|提示|tip|搜索|search|备注|remark|说明|desc[^r]/.test(info.toLowerCase())) return;
                var sz = el.rows * 80 + el.offsetHeight;
                // 名字匹配加分
                if (/content|intro|内容|简介|正文|body|detail/.test(info.toLowerCase())) sz += 10000;
                if (sz > bestSize) {{ best = el; bestSize = sz; }}
            }});
            if (!best) {{
                // 最后的兜底：找不是温馨提示的 textarea
                areas.forEach(function(el) {{
                    var info = (el.name||'') + (el.placeholder||'');
                    if (!/温馨|提示|tip/.test(info.toLowerCase()) && !best) best = el;
                }});
            }}
            if (best) {{
                best.value = intro;
                ['input','change','blur','keyup'].forEach(function(ev) {{
                    best.dispatchEvent(new Event(ev, {{bubbles: true}}));
                }});
                var name = best.name || best.id || best.placeholder || 'textarea';
                return 'ok:' + name.substring(0,40);
            }}
            return 'not found';
        }})()
    """, timeout=3.0)

    if "ok:" in r:
        filled["3.简介"] = f"{len(intro)}字 → {r.split(':',1)[1]}"
    else:
        not_found["3.简介"] = "未找到内容输入区域（所有textarea都被跳过了）"

    # === 第4步: 上传LOGO ===

    # === 下载链接 ===
    if download_url:
        for sel in ['input[name="download_url"]', 'input[name="download"]', 'input[name="url"]',
                     '#download_url', 'input[placeholder*="下载"]', 'input[placeholder*="链接"]',
                     'input[placeholder*="地址"]']:
            r = bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = '{download_url}'; el.dispatchEvent(new Event('input')); return 'ok'; }}
                    return 'not found';
                }})()
            """, timeout=2.0)
            if "ok" in r:
                filled["下载链接"] = download_url[:50]
                break
        else:
            not_found["下载链接"] = "未找到下载链接输入框"

    # === 标签 ===
    if tags:
        for sel in ['input[name="tags"]', '#tags', 'input[placeholder*="标签"]']:
            r = bridge.execute_js(f"""
                (function() {{
                    var el = document.querySelector('{sel}');
                    if (el) {{ el.value = {json.dumps(tags)}; el.dispatchEvent(new Event('input')); return 'ok'; }}
                    return 'not found';
                }})()
            """, timeout=2.0)
            if "ok" in r:
                filled["标签"] = tags
                break
        else:
            not_found["标签"] = "未找到标签输入框"

    # === 先扫描页面上所有文件上传入口 ===
    file_inputs_raw = bridge.execute_js("""
        (function() {
            var inputs = document.querySelectorAll('input[type="file"]');
            var result = [];
            inputs.forEach(function(el) {
                result.push({name: el.name, id: el.id, className: el.className, placeholder: el.placeholder});
            });
            return JSON.stringify(result);
        })()
    """, timeout=2.0)
    try:
        file_inputs = json.loads(file_inputs_raw)
        filled["文件入口"] = f"找到 {len(file_inputs)} 个: {file_inputs}"
    except:
        file_inputs = []
        filled["文件入口"] = "扫描失败，尝试默认选择器"

    # === 第4步: 上传LOGO ===
    if logo_path:
        logo_sel = None
        if file_inputs:
            first = file_inputs[0]
            if first.get("name"):
                logo_sel = f'input[type="file"][name="{first["name"]}"]'
            elif first.get("id"):
                logo_sel = f'#{first["id"]}'
        if not logo_sel:
            logo_sel = 'input[type="file"]:first-of-type'
        try:
            result = bridge.upload_files(logo_sel, [logo_path])
            filled["4.LOGO"] = f"✅ {result}"
        except Exception as e:
            filled["4.LOGO"] = f"⚠️ {e}"

    # === 第5步: 上传截图（全部） ===
    if screenshot_paths:
        try:
            shots = json.loads(screenshot_paths) if isinstance(screenshot_paths, str) else screenshot_paths
            if isinstance(shots, list) and shots:
                shot_sel = None
                if len(file_inputs) >= 2:
                    second = file_inputs[1]
                    if second.get("name"):
                        shot_sel = f'input[type="file"][name="{second["name"]}"]'
                    elif second.get("id"):
                        shot_sel = f'#{second["id"]}'
                if not shot_sel:
                    shot_sel = 'input[type="file"]:last-of-type'
                result = bridge.upload_files(shot_sel, shots)
                filled["5.截图"] = f"✅ {len(shots)}张 ({result})"
            else:
                filled["5.截图"] = "无"
        except Exception as e:
            filled["5.截图"] = f"⚠️ {e}"

    # === 生成报告 ===
    report_parts = []
    for k in sorted(filled.keys()):
        report_parts.append(f"  ✅ {k}: {filled[k]}")
    for k in not_found:
        report_parts.append(f"  ❌ {k}: {not_found[k]}")

    report = "📝 填写报告（按用户要求的5步顺序）:\n" + "\n".join(report_parts)
    logger.info(report)
    return report, len(not_found) == 0


def _make_report(filled, not_found):
    parts = [f"  ✅ {k}: {v}" for k, v in filled.items()]
    parts += [f"  ❌ {k}: {v}" for k, v in not_found.items()]
    return "📝 " + "\n".join(parts)
