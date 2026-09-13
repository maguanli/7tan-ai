# 7Tan 插件开发指南

> 面向插件开发者的官方文档。学会本文，你就能为 7Tan 开发插件，上架赚钱。

## 一、插件是什么

插件是 7Tan 的功能扩展包。一个插件 = 一个目录 + 若干个「工具」（tool）。
AI 助手（也就是我）通过调用工具来干活——搜索、发布、写文章、控制桌面……

**举例**：`viral_writer` 插件提供 6 个工具（爆款选题、标题、大纲、正文、金句、质检），让 AI 能一键生成公众号爆款文章。

## 二、目录结构

```
data/plugins/<插件ID>/
├── tools.py          ← 核心：工具代码（必需）
├── plugin.json       ← 插件元数据（远程安装时自动生成）
└── license.py        ← 付费插件才需要（授权验证）
```

`<插件ID>` 必须是小写英文字母 + 下划线，如 `my_plugin`。

## 三、第一个插件（Hello World）

在 `data/plugins/hello_world/tools.py` 写入：

```python
"""
示例插件 — 打招呼
"""
import sys
from pathlib import Path

# 固定三行：把项目根目录加入搜索路径，导入注册器
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool


@register_tool(
    name="hello_world",
    description="跟用户打个招呼。用于演示插件开发。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "你的名字"},
        },
        "required": ["name"]
    },
    category="demo",
)
def hello_world(name: str) -> str:
    """打招呼"""
    return f"👋 你好，{name}！我是 7Tan 插件，很高兴认识你！"
```

重启 7Tan 后，AI 的工具列表里就会出现 `hello_world`。

## 四、register_tool 接口详解

`register_tool` 是唯一必须的注册入口，参数如下：

| 参数 | 必填 | 说明 |
|---|---|---|
| `name` | ✅ | 工具名（小写字母+下划线），全局唯一 |
| `description` | ✅ | 一句话描述，**AI 靠它判断何时调用，写清楚** |
| `parameters` | ✅ | JSON Schema 格式的参数定义（type/properties/required） |
| `category` | ❌ | 分类标签，便于管理 |

**函数规范**：
- 参数名、类型必须和 `parameters.properties` 一致
- 返回值必须是 `str`（或能转成 str）
- 返回信息要有表情符号/编号，让 AI 好读

## 五、插件元数据（manifest 注册）

插件要被识别，需在 `data/plugins/manifest.json` 注册：

```json
{
  "id": "hello_world",
  "name": "示例插件",
  "version": "1.0.0",
  "author": "你的名字",
  "type": "remote",
  "category": "工具",
  "description": "演示用插件",
  "tools": ["hello_world"],
  "icon": "👋"
}
```

| 字段 | 说明 |
|---|---|
| `type` | `builtin`（随软件内置）/ `custom`（自定义）/ `remote`（远程下载）/ `paid`（付费） |
| `tools` | 该插件提供的所有工具名数组 |

## 六、分发方式

### 方式 A：随软件内置
把插件目录放进 `data/plugins/`，提交给官方合并。适用于免费基础插件。

### 方式 B：远程安装（推荐第三方）
1. 把你的 `tools.py` 放到任意 HTTP 服务器（如 Gitee Pages / 自己的网站）
2. manifest 里填写 `"type": "remote", "source_url": "https://你的地址/tools.py"`
3. 用户在软件内执行插件安装，自动下载并加载

### 方式 C：付费插件（上架赚钱）
接入授权验证，见下一节。

## 七、付费插件接入（重要）

1. **联系官方**（QQ: 773178032 / 微信: wap801276 / 充值页 https://www.7tan.com/task/wallet.php）申请上架资格。
2. 参考 `data/plugins/viral_writer/` 的完整实现：
   - `license.py` — 授权核心：RSA 签名验证 + 设备指纹绑定 + 试用计数
   - `gen_license.py` — 授权码签发工具（只有你有私钥，伪造不了）
   - `tools.py` — 每个工具入口加一道付费闸门
3. 收费模式：官方代收（平台分成）或 开发者直收，与官方协商。

## 八、安全红线（违反直接下架）

| 🚫 禁止 | 说明 |
|---|---|
| 读取/上传用户 API Key、Token | 插件无权访问其他插件的密钥 |
| 恶意代码 | 木马、勒索、挖矿、远控一律封禁 |
| 控制微信/支付宝等发送转账消息 | 自动化诈骗 |
| 收集用户隐私并外传 | 用户数据只属于用户 |
| 代码混淆/加密 | 插件必须可审计 |

## 九、上架流程

```
1. 开发完成（本地自测通过）
2. 提交：插件目录打包 + 说明文档 → 联系官方审核
3. 审核：功能/安全/合规检查（约 1-3 个工作日）
4. 上架：官方签名后进入插件市场
5. 收益：按约定分成结算
```

## 十、FAQ

- **Q：插件要钱吗？** A：开发免费，上架免费。你卖多少钱官方审核后定价。
- **Q：AI 怎么知道用我的插件？** A：工具 description 写清楚，AI 遇到对应任务会自动调用。
- **Q：插件能访问文件系统吗？** A：能，Python 代码可以读任意文件——但**安全红线禁止滥用**，审核会查。
- **Q：付费插件怎么防破解？** A：授权码 RSA-2048 签名 + 绑定设备指纹，私钥在官方手里，开源也伪造不了。

---

祝开发顺利！有问题到 7坛社区（https://www.7tan.com/bbs/）发帖。
