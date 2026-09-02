# -*- coding: utf-8 -*-
"""
7Tan 模块G：工具调度与自主脚本执行引擎
======================================
三大子系统：
1. ToolRegistry 工具注册表：统一收录7Tan自有工具，AI原生优先调用自家工具
2. ScriptGenerator 脚本生成决策：判断用现有工具 还是 自主编写脚本
3. SandboxRunner 沙盒安全规则：静态审查/白名单/资源限制/快照回退

模块G补齐认知闭环的行动层：动机B→思考E→行动G→反馈→学习F→沉淀A→安全D
"""

import os
import json
import datetime

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(MODULE_DIR), "data", "module_g")
REGISTRY_FILE = os.path.join(DATA_DIR, "tool_registry.json")
USAGE_LOG_FILE = os.path.join(DATA_DIR, "usage_log.jsonl")

# ---------------------------------------------------------------
# 工具注册表（内置精简版，详细版可由 registry_save 导出为JSON）
# 字段：name 工具名 | desc 功能描述 | scene 适用场景 | risk 风险等级(1-5) | dep 依赖
# ---------------------------------------------------------------
BUILTIN_REGISTRY = {
    "7坛社区采集发布": [
        {"name": "browse_page", "desc": "打开网页并获取页面内容摘要(含文字/链接/图片URL)", "scene": "浏览源站详情页、列表页", "risk": 1, "dep": "源站浏览器"},
        {"name": "click_element", "desc": "在浏览器中点击指定元素", "scene": "导航、翻页、触发下载", "risk": 1, "dep": "源站浏览器"},
        {"name": "find_download_links", "desc": "在当前页面查找下载链接(APK/IPA/ZIP等)", "scene": "从下载站定位真实下载URL", "risk": 1, "dep": "源站浏览器"},
        {"name": "download_file", "desc": "下载文件到本地,支持断点续传", "scene": "下载游戏包/软件包", "risk": 1, "dep": "网络"},
        {"name": "db_check_duplicate", "desc": "按源站ID检查资源是否已存在", "scene": "采集前去重", "risk": 1, "dep": "数据库"},
        {"name": "db_save_resource", "desc": "保存资源信息到数据库", "scene": "采集后入库", "risk": 1, "dep": "数据库"},
        {"name": "db_add_task_log", "desc": "记录任务日志(browse/download/rewrite/upload/publish)", "scene": "任务状态追踪", "risk": 1, "dep": "数据库"},
        {"name": "oss_upload", "desc": "上传文件到云存储,返回外链URL", "scene": "包体上云、图片上云", "risk": 1, "dep": "OSS"},
        {"name": "publish_to_7tan", "desc": "发布资源到7坛(自动填表、上传LOGO/截图、提交)", "scene": "最终发布", "risk": 1, "dep": "管理后台"},
        {"name": "api_publish_to_7tan", "desc": "通过API发布资源到7坛(比浏览器自动化更快)", "scene": "最终发布(API方式)", "risk": 1, "dep": "API"},
    ],
    "浏览器/网页工具": [
        {"name": "use_source_browser", "desc": "切换到源站浏览器", "scene": "在游戏源站操作前", "risk": 1, "dep": "浏览器"},
        {"name": "use_admin_browser", "desc": "切换到管理后台浏览器", "scene": "在7坛后台操作前", "risk": 1, "dep": "浏览器"},
        {"name": "screenshot", "desc": "对当前页面截图保存到本地", "scene": "留证、检查页面", "risk": 1, "dep": "浏览器"},
        {"name": "get_page_images", "desc": "获取当前页面所有图片URL", "scene": "提取游戏LOGO/截图", "risk": 1, "dep": "浏览器"},
        {"name": "extract_logo", "desc": "自动识别并下载LOGO/图标", "scene": "获取游戏图标", "risk": 1, "dep": "浏览器"},
        {"name": "auto_screenshot", "desc": "自动截取高质量预览图", "scene": "获取游戏详情页截图", "risk": 1, "dep": "浏览器"},
        {"name": "browser_exec_js", "desc": "在页面执行JavaScript", "scene": "填表、读DOM、触发事件", "risk": 2, "dep": "浏览器"},
        {"name": "browser_set_value", "desc": "设置输入框的值(兼容React)", "scene": "填表", "risk": 1, "dep": "浏览器"},
        {"name": "login_7tan", "desc": "登录7坛管理后台", "scene": "后台操作前", "risk": 2, "dep": "浏览器"},
    ],
    "本地文件/文档": [
        {"name": "list_files", "desc": "列出目录下所有文件", "scene": "查看下载目录", "risk": 1, "dep": "无"},
        {"name": "read_file_content", "desc": "读取文件内容(文本/JSON)", "scene": "读取文档、日志、配置", "risk": 1, "dep": "无"},
        {"name": "write_file", "desc": "写入文件(文本/二进制)", "scene": "生成脚本、导出TXT", "risk": 1, "dep": "无"},
        {"name": "delete_file", "desc": "删除本地文件或目录", "scene": "清理临时文件", "risk": 3, "dep": "无"},
        {"name": "file_replace", "desc": "对文本文件批量字符串替换", "scene": "批量修改配置/代码", "risk": 2, "dep": "无"},
        {"name": "compress_image", "desc": "压缩图片(LOGO/截图)", "scene": "减小图片体积", "risk": 1, "dep": "无"},
    ],
    "脚本生成/执行": [
        {"name": "sandbox_execute", "desc": "在安全沙盒执行Python脚本(30秒超时)", "scene": "验证自生代码、跑算法", "risk": 2, "dep": "沙盒"},
        {"name": "run_shell_script", "desc": "执行Shell脚本", "scene": "批量命令、自动化", "risk": 3, "dep": "Shell"},
        {"name": "run_command", "desc": "执行任意shell命令", "scene": "构建、运行脚本文件", "risk": 3, "dep": "Shell"},
        {"name": "write_file+run_command", "desc": "先写脚本文件再运行(标准ScriptGenerator流程)", "scene": "多步骤/循环/批量任务", "risk": 2, "dep": "Shell"},
    ],
    "桌面自动化": [
        {"name": "desktop_see", "desc": "看懂屏幕(截图+OCR+视觉理解)", "scene": "查看桌面状态", "risk": 1, "dep": "桌面"},
        {"name": "desktop_ocr", "desc": "屏幕OCR识别文字", "scene": "读取界面文字", "risk": 1, "dep": "桌面"},
        {"name": "desktop_click_text", "desc": "按文字定位点击", "scene": "操作按钮/菜单", "risk": 2, "dep": "桌面"},
        {"name": "desktop_type_text", "desc": "向焦点输入文本", "scene": "输入内容", "risk": 1, "dep": "桌面"},
        {"name": "desktop_send_chat", "desc": "聊天软件自动发消息(带防发错闸门)", "scene": "微信/QQ发消息", "risk": 2, "dep": "桌面"},
        {"name": "desktop_watch", "desc": "桌面连续监控(帧差检测)", "scene": "等弹窗、盯进度", "risk": 1, "dep": "桌面"},
    ],
    "自我进化/安全": [
        {"name": "memory_store", "desc": "存储知识/记忆到持久化存储", "scene": "沉淀经验", "risk": 1, "dep": "记忆库"},
        {"name": "memory_recall", "desc": "检索已存储的记忆", "scene": "回忆经验", "risk": 1, "dep": "记忆库"},
        {"name": "self_update_prompt", "desc": "更新系统提示词/子任务模板", "scene": "自我优化", "risk": 4, "dep": "核心"},
        {"name": "self_modify_config", "desc": "修改配置文件(config.yaml)", "scene": "调整参数", "risk": 4, "dep": "核心"},
        {"name": "create_plugin", "desc": "动态创建新插件扩展能力", "scene": "自我扩展", "risk": 4, "dep": "核心"},
        {"name": "self_rebuild", "desc": "重新构建打包整个项目", "scene": "源码改动后", "risk": 5, "dep": "构建"},
        {"name": "self_restart", "desc": "自动重启应用程序", "scene": "构建后重启", "risk": 4, "dep": "核心"},
        {"name": "verify_integrity", "desc": "验证自身文件SHA-256完整性", "scene": "安全自检", "risk": 1, "dep": "核心"},
        {"name": "check_sensitive_words", "desc": "检查文本敏感词", "scene": "发布前审核", "risk": 1, "dep": "审核"},
        {"name": "check_content_quality", "desc": "检查内容质量(简介长度/截图数)", "scene": "发布前质检", "risk": 1, "dep": "审核"},
    ],
    "内容创作/AI": [
        {"name": "web_search", "desc": "搜索互联网获取资讯", "scene": "查攻略/评测/新闻", "risk": 1, "dep": "网络"},
        {"name": "fetch_news", "desc": "获取游戏行业新闻", "scene": "了解行业动态", "risk": 1, "dep": "网络"},
        {"name": "translate_text", "desc": "英文翻译为中文", "scene": "翻译Steam商店描述", "risk": 1, "dep": "翻译"},
        {"name": "cloud_write_intro", "desc": "深度模式撰写游戏发布简介(HTML)", "scene": "写发布文案", "risk": 1, "dep": "云端AI"},
        {"name": "analyze_game", "desc": "深度分析游戏生成结构化报告", "scene": "写推荐文章", "risk": 1, "dep": "云端AI"},
        {"name": "compare_games", "desc": "对比两款游戏差异", "scene": "竞品对比文章", "risk": 1, "dep": "云端AI"},
        {"name": "summarize_reviews", "desc": "汇总用户评价提取正负面主题", "scene": "评价分析", "risk": 1, "dep": "云端AI"},
    ],
    "开发/运维": [
        {"name": "git_*", "desc": "Git全套: status/diff/commit/push/pull/branch", "scene": "版本管理", "risk": 2, "dep": "Git"},
        {"name": "docker_*", "desc": "Docker: ps/images/compose/logs/build", "scene": "容器运维", "risk": 3, "dep": "Docker"},
        {"name": "kubectl_*", "desc": "K8s: get/apply/logs/exec/scale等", "scene": "集群运维", "risk": 4, "dep": "K8s"},
        {"name": "run_tests", "desc": "自动检测并运行项目测试", "scene": "测试验证", "risk": 1, "dep": "pytest等"},
        {"name": "code_review_file", "desc": "单文件静态分析与质量审查", "scene": "代码审查", "risk": 1, "dep": "分析器"},
    ],
    "特色扩展": [
        {"name": "gzh_full_flow", "desc": "公众号发布全流程(填标题/正文/摘要/封面/存草稿)", "scene": "公众号发文", "risk": 2, "dep": "桌面"},
        {"name": "viral_topic/title/outline/write", "desc": "爆款内容生成套件", "scene": "自媒体选题/标题/大纲/正文", "risk": 1, "dep": "云端AI"},
        {"name": "novel_quality_check", "desc": "番茄小说质检引擎", "scene": "小说发布前自查", "risk": 1, "dep": "分析器"},
        {"name": "ltz_*", "desc": "龙头识别/情绪温度计/复盘/模拟交易", "scene": "股票分析", "risk": 3, "dep": "行情API"},
        {"name": "iching_*", "desc": "易经占卦/查卦/每日一卦", "scene": "传统文化问答", "risk": 1, "dep": "无"},
        {"name": "sunzi_*", "desc": "孙子兵法问答/推演/每日兵法", "scene": "谋略咨询", "risk": 1, "dep": "无"},
    ],
}


def _ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)


def registry_list(category=""):
    """模块G·工具注册表查询：列出工具清单。category留空=全部(按分类返回)。"""
    if category:
        items = BUILTIN_REGISTRY.get(category, [])
        return json.dumps({"category": category, "count": len(items), "tools": items}, ensure_ascii=False, indent=2)
    result = {k: v for k, v in BUILTIN_REGISTRY.items()}
    total = sum(len(v) for v in result.values())
    return json.dumps({"total": total, "categories": result}, ensure_ascii=False, indent=2)


def registry_save():
    """模块G·导出注册表：把内置工具注册表导出为JSON文件，供详细查阅。"""
    _ensure_data_dir()
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(BUILTIN_REGISTRY, f, ensure_ascii=False, indent=2)
    return json.dumps({"ok": True, "path": REGISTRY_FILE, "total": sum(len(v) for v in BUILTIN_REGISTRY.values())}, ensure_ascii=False)


def match_tool(task_desc):
    """模块G·任务→工具匹配：根据任务描述关键词，返回最匹配的工具(按适用度排序)。"""
    if not task_desc:
        return json.dumps({"error": "请提供任务描述 task_desc"}, ensure_ascii=False)
    KEYWORD_MAP = [
        (["下载", "游戏包", "apk", "ipa", "zip"], "download_file"),
        (["发布", "上传到7坛", "提交发布"], "publish_to_7tan"),
        (["去重", "是否已存在", "重复"], "db_check_duplicate"),
        (["入库", "保存资源", "存数据库"], "db_save_resource"),
        (["搜索", "查攻略", "查评测", "搜一下"], "web_search"),
        (["截图", "截屏"], "screenshot"),
        (["识别", "ocr", "读文字"], "desktop_ocr"),
        (["写脚本", "跑脚本", "执行python", "验证代码"], "sandbox_execute"),
        (["写文件", "生成txt", "导出", "保存到本地"], "write_file"),
        (["读文件", "查看文件", "读取"], "read_file_content"),
        (["上传oss", "上云", "外链"], "oss_upload"),
        (["查记忆", "回忆", "记住", "记忆"], "memory_recall"),
        (["存记忆", "记住这个"], "memory_store"),
        (["翻译"], "translate_text"),
        (["写简介", "写文案", "写文章", "写介绍"], "cloud_write_intro"),
        (["发微信", "发消息", "聊天发送"], "desktop_send_chat"),
        (["公众号", "发文"], "gzh_full_flow"),
        (["测试", "pytest"], "run_tests"),
        (["git", "提交", "commit"], "git_commit"),
        (["占卦", "易经", "算卦"], "iching_divine"),
        (["兵法", "孙子"], "sunzi_ask"),
        (["龙头", "复盘", "涨停"], "ltz_leader"),
    ]
    task_lower = task_desc.lower()
    scores = {}
    for keywords, tool in KEYWORD_MAP:
        for kw in keywords:
            if kw.lower() in task_lower:
                scores[tool] = scores.get(tool, 0) + 1
    if not scores:
        return json.dumps({"match": False, "suggestion": "未匹配到具体工具，可查询 registry_list() 浏览全部注册表"}, ensure_ascii=False)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top = ranked[0][0]
    info = None
    for cat, tools in BUILTIN_REGISTRY.items():
        for t in tools:
            if t["name"] == top or top in t["name"]:
                info = dict(t, category=cat)
                break
    return json.dumps({"match": True, "top_tool": top, "score": scores[top], "info": info, "all": [r[0] for r in ranked[:3]]}, ensure_ascii=False)


def script_decision(task_desc):
    """模块G·脚本生成决策：判断该用现有工具 还是 需要自写脚本。
    规则：简单/单步→现有工具；多步骤/循环/批量/非标→写脚本。"""
    if not task_desc:
        return json.dumps({"error": "请提供任务描述"}, ensure_ascii=False)
    t = task_desc.lower()
    script_hints = ["循环", "批量", "遍历", "多步骤", "串联", "重复", "所有", "每个", "定时", "轮询",
                    "for ", "while", "递归", "统计", "汇总所有", "逐一", "自动化流程"]
    hit = [h for h in script_hints if h in t]
    if hit:
        return json.dumps({
            "decision": "SCRIPT", "reason": "检测到脚本特征词: " + str(hit),
            "action": "进入ScriptGenerator: 用write_file写脚本 → sandbox_execute/run_command运行 → 异常自动修复",
            "safety": "遵守SandboxRunner四层防护(静态审查/白名单/资源限制/快照回退)"
        }, ensure_ascii=False)
    m = json.loads(match_tool(t))
    if m.get("match"):
        return json.dumps({
            "decision": "TOOL", "reason": "任务可被现有工具覆盖，优先官方原生工具执行(最快最稳)",
            "action": "直接调用: " + m["top_tool"]
        }, ensure_ascii=False)
    return json.dumps({
        "decision": "SCRIPT", "reason": "无匹配工具，需要自定义脚本",
        "action": "进入ScriptGenerator自主编写脚本"
    }, ensure_ascii=False)


def sandbox_rules():
    """模块G·沙盒执行四层安全规则：写脚本前必须遵守。"""
    rules = {
        "layer1_static_review": ["拦截删除文件/目录", "拦截格式化磁盘", "拦截提权操作", "拦截恶意联网", "拦截高危系统调用(rm -rf/shutdown/format)"],
        "layer2_whitelist_import": ["仅允许: os(安全子集)/json/re/datetime/pathlib/collections/标准库", "禁止: subprocess危险用法/ctypes/socket外联/requests外网"],
        "layer3_resource_limit": ["最大运行时间: 30秒(沙盒)", "禁止死循环常驻", "禁止超大内存分配"],
        "layer4_snapshot_rollback": ["执行前Git快照", "出错自动回退", "全程日志审计"],
        "principle": "AI随便写脚本、随便试错，不会弄坏电脑、不会破坏系统"
    }
    return json.dumps(rules, ensure_ascii=False, indent=2)


def log_usage(tool_name, status, note=""):
    """模块G·记录工具调用经验日志，供模块F复盘学习(成功/失败案例沉淀)。"""
    _ensure_data_dir()
    entry = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tool": tool_name,
        "status": status,
        "note": note,
        "module": "G"
    }
    with open(USAGE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return json.dumps({"ok": True, "logged": entry}, ensure_ascii=False)


def g_flow(task_desc):
    """模块G·总入口：任务描述 → 决策(工具 or 脚本) → 输出行动方案。"""
    if not task_desc:
        return json.dumps({"error": "请提供任务描述"}, ensure_ascii=False)
    d = json.loads(script_decision(task_desc))
    result = {"task": task_desc, "decision": d}
    if d["decision"] == "TOOL":
        m = json.loads(match_tool(task_desc))
        result["plan"] = [{"step": 1, "action": "调用工具 " + m["top_tool"], "desc": (m["info"]["desc"] if m.get("info") else "")}]
    else:
        result["plan"] = [
            {"step": 1, "action": "write_file 生成脚本", "desc": "基于7Tan官方工具能力编写, 加异常捕获和日志"},
            {"step": 2, "action": "sandbox_execute / run_command 运行", "desc": "遵守四层沙盒防护"},
            {"step": 3, "action": "结果复盘", "desc": "成功→经验入库(memory_store); 失败→自动修复迭代"},
        ]
    return json.dumps(result, ensure_ascii=False, indent=2)
