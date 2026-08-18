# 7Tan AI — 插件开发指南

## 快速开始

在 `data/plugins/<plugin_id>/tools.py` 中编写工具函数：

```python
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

@register_tool(
    name="my_tool",
    description="工具功能描述",
    parameters={
        "type": "object",
        "properties": {
            "arg1": {"type": "string", "description": "参数说明"},
        },
        "required": ["arg1"]
    },
    category="custom"
)
def my_tool(arg1: str) -> str:
    """工具实现"""
    return f"结果: {arg1}"
```

## 注册插件

1. 创建目录 `data/plugins/my_plugin/`
2. 写入 `tools.py`（如上）
3. 在 `data/plugins/manifest.json` 添加条目：
```json
{
  "id": "my_plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "type": "builtin",
  "category": "自定义",
  "description": "描述",
  "tools": ["my_tool"],
  "icon": "🔧"
}
```
4. 在 `data/plugins/installed.json` 的 plugins 数组中添加 `"my_plugin"`
5. 重启 7Tan 即可使用

## 工具分类

| category | 用途 | 示例 |
|----------|------|------|
| `search` | 搜索工具 | grep_code, web_search |
| `code` | 代码分析 | list_functions, analyze_imports |
| `lsp` | 语言服务 | go_to_definition, get_diagnostics |
| `refactor` | 重构 | rename_symbol, format_code |
| `test` | 测试 | run_tests, discover_tests |
| `terminal` | 终端 | run_command, run_build |
| `db` | 数据库 | explore_db, query_db |
| `cicd` | CI/CD | generate_ci_config |
| `debug` | 调试 | analyze_error |
| `config` | 配置 | manage_env, scan_secrets |
| `api` | HTTP | http_request |
| `diff` | 差异 | generate_diff |
| `scaffold` | 脚手架 | create_project |
| `doc` | 文档 | generate_readme |
| `deploy` | 部署 | check_dependencies |
| `custom` | 自定义 | 用户自定义 |

## 工具函数规范

- **必须有类型注解** — AI 根据类型自动匹配参数
- **返回字符串** — 结果直接展示给 AI
- **不要有副作用** — 除非明确标注为危险工具
- **超时保护** — subprocess 调用必须有 timeout
- **异常处理** — 工具函数内部捕获所有异常，返回错误字符串

## 最佳实践

- 使用 `subprocess.CREATE_NO_WINDOW` 避免弹黑窗
- 大结果截断到 5000 字符以内
- 使用 descriptive 函数名（不要缩写）
- 复杂工具拆分：一个工具做一件事
