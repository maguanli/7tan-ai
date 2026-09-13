# 7Tan 架构文档

> 最后更新：2025-07-14  
> 涵盖：收费方案、登录系统、API接口、防破解、新手引导、安全修改

---

## 一、收费方案

### 1.1 版本对比

| | 基础版 | 专业版 |
|:--|:--|:--|
| 价格 | 免费 | **200元/半年** |
| AI 聊天 | ✅ | ✅ |
| 写代码 | ✅ | ✅ |
| 游戏分析 | ✅ | ✅ |
| 游戏发布 | ✅ | ✅ |
| **修改软件自身文件** | ❌ | ✅ |
| AI Key | 自带 | 自带 |
| 试用 | 3次无需Key | — |

### 1.2 支付流程

```
软件内点 [续费] → 跳转 7tan.com 支付页面 → 支付完成
→ 回软件点 [刷新状态] → 验证API → 签发新Token
```

**软件本身不处理支付，只放跳转按钮。**

---

## 二、登录系统

### 2.1 登录方式

| 项目 | 方案 |
|:--|:--|
| 登录方式 | **用户名 或 手机号** + 密码 |
| 输入框标签 | `👤 用户名 或 手机号` |
| 记住登录 | **30天** |
| 离线可用 | Token 本地 RSA 验签，不强制联网 |
| 注册/找回密码 | 跳转 7tan.com 网页 |

### 2.2 登录界面设计

```
┌──────────────────────────────────────┐
│         登录 7Tan                    │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ 👤 用户名 或 手机号            │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 🔒 密码                   [👁] │ │
│  └────────────────────────────────┘ │
│                                      │
│  [√] 记住登录（30天）  [忘记密码？]  │
│                                      │
│  ┌────────────────────────────────┐ │
│  │         登  录                  │ │
│  └────────────────────────────────┘ │
│                                      │
│  ────────── 或 ──────────           │
│                                      │
│  ┌────────────────────────────────┐ │
│  │     🎁 免注册试用 3 次         │ │
│  └────────────────────────────────┘ │
│                                      │
│  还没有账号？[立即注册 →]            │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ 🔒 离线模式（上次登录有效期内） │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### 2.3 数据库变更（ll_useregs 表）

```sql
ALTER TABLE ll_useregs ADD COLUMN pro_expires INT DEFAULT 0;    -- 专业版过期时间戳
ALTER TABLE ll_useregs ADD COLUMN pro_activated INT DEFAULT 0;  -- 专业版激活时间戳
```

### 2.4 登录SQL

```sql
-- 支持用户名或手机号登录
SELECT * FROM ll_useregs 
WHERE ll_name = ? OR ll_shouji = ?
```

---

## 三、API 接口（7tan.com 新建）

### 3.1 接口列表

| 文件 | 方法 | 用途 | 说明 |
|:--|:--|:--|:--|
| `api/auth/login.php` | POST | 登录 | 验证用户名/手机号+密码，返回 JWT Token |
| `api/auth/verify.php` | GET | 验证 | 验证 Token 有效性 + 查询会员状态 |
| `api/auth/refresh.php` | POST | 刷新 | 续费后刷新 Token（更新 pro 状态） |

### 3.2 JWT Token 结构

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "uid": 12345,
    "name": "用户名",
    "level": "pro",
    "iat": 1720000000,
    "exp": 1722592000
  },
  "signature": "RSA-SHA256签名"
}
```

| 字段 | 说明 |
|:--|:--|
| `uid` | 用户 ID |
| `name` | 用户名 |
| `level` | `basic` 或 `pro` |
| `iat` | 签发时间 |
| `exp` | 过期时间（30天后） |

### 3.3 login.php 伪代码

```php
<?php
// api/auth/login.php
$input = json_decode(file_get_contents('php://input'), true);
$account = $input['account'];  // 用户名或手机号
$password = $input['password'];

// 查数据库
$user = $db->query(
    "SELECT ll_uid, ll_name, ll_mima, ll_shouji, pro_expires 
     FROM ll_useregs 
     WHERE ll_name = ? OR ll_shouji = ?",
    [$account, $account]
)->fetch();

if (!$user || !password_verify($password, $user['ll_mima'])) {
    http_response_code(401);
    echo json_encode(['error' => '用户名或密码错误']);
    exit;
}

// 判断会员等级
$now = time();
$level = ($user['pro_expires'] > $now) ? 'pro' : 'basic';

// 签发JWT
$payload = [
    'uid' => $user['ll_uid'],
    'name' => $user['ll_name'],
    'level' => $level,
    'iat' => $now,
    'exp' => $now + 30 * 86400,  // 30天
];
$jwt = jwt_encode($payload, $private_key, 'RS256');

echo json_encode(['token' => $jwt, 'user' => $payload]);
```

---

## 四、防破解方案（仅两层，不做混淆）

### 4.1 架构总览

```
┌─────────────────────────────────┐
│  核心验证函数 (Cython → .pyd)    │  ← 二进制，无法反编译
│  license_verify.py              │
│  rsa_verify.py                  │
│  safe_modify.py                 │
├─────────────────────────────────┤
│  敏感字符串 (AES手动加密)       │  ← strings 命令提取不到
│  RSA公钥、API端点URL            │
├─────────────────────────────────┤
│  其余代码 (明码 .py)            │  ← 不做混淆
│  UI / 插件 / 业务逻辑           │
└─────────────────────────────────┘
```

### 4.2 不做 PyArmor 混淆的原因

- 混淆会导致性能下降 10-30%
- 错误堆栈变天书，调试困难
- 反射/动态调用失效（影响插件系统）
- PyInstaller 打包兼容性问题
- **真正防破解靠 Cython .pyd，不靠混淆**

### 4.3 新增文件结构

```
src/security/
├── __init__.py
├── license_verify.py    ← 验证入口（Cython编译→.pyd）
├── rsa_verify.py        ← RSA验签实现（Cython编译→.pyd）
├── safe_modify.py       ← 安全修改门控（Cython编译→.pyd）
├── strings.py           ← 敏感字符串（AES加密存储）
└── public_key.pem       ← RSA公钥（明文，验签用）
```

### 4.4 license_verify.py（编译成 .pyd）

```python
"""授权验证模块 - Cython编译后为二进制"""
import time
import json
from .rsa_verify import rsa_verify
from .strings import get_public_key

def verify_license(token_str: str) -> dict:
    """
    验证授权令牌，返回用户权限信息。
    编译成 .pyd 后无法被反编译。
    """
    pub_key = get_public_key()  # 运行时从加密字符串解密
    payload = rsa_verify(token_str, pub_key)
    
    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise LicenseExpired("授权已过期，请续费")
    
    if payload.get("iat", 0) > now + 86400:
        raise LicenseInvalid("令牌无效")
    
    return {
        "user_id": payload["uid"],
        "level": payload["level"],
        "expires_at": payload["exp"],
    }

class LicenseExpired(Exception):
    pass

class LicenseInvalid(Exception):
    pass
```

### 4.5 rsa_verify.py（编译成 .pyd）

```python
"""RSA验签实现 - Cython编译后为二进制"""
import hashlib
import base64
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

def rsa_verify(token_str: str, public_key_pem: str) -> dict:
    """验证 JWT 的 RSA 签名，返回 payload"""
    parts = token_str.split(".")
    if len(parts) != 3:
        raise ValueError("令牌格式无效")
    
    header_b64, payload_b64, sig_b64 = parts
    sig_bytes = _base64url_decode(sig_b64)
    message = f"{header_b64}.{payload_b64}".encode()
    public_key = load_pem_public_key(public_key_pem.encode())
    
    try:
        public_key.verify(
            sig_bytes, message,
            padding.PKCS1v15(), hashes.SHA256()
        )
    except Exception:
        raise ValueError("签名验证失败，令牌可能被篡改")
    
    payload_json = _base64url_decode(payload_b64).decode()
    return json.loads(payload_json)

def _base64url_decode(data: str) -> bytes:
    data = data.replace("-", "+").replace("_", "/")
    padding_len = 4 - len(data) % 4
    if padding_len != 4:
        data += "=" * padding_len
    return base64.b64decode(data)
```

### 4.6 strings.py（手动加密存储，不编译）

```python
"""敏感字符串 - AES加密存储，运行时解密"""
import base64
from Crypto.Cipher import AES

# === 加密存储（AES加密后的base64） ===
_PUBLIC_KEY_ENCRYPTED = "x7KpQm3v...（AES加密后的base64）"
_API_LOGIN_ENCRYPTED = "R8sTqL2n...（AES加密后的base64）"
_API_VERIFY_ENCRYPTED = "M3wXkJ9a...（AES加密后的base64）"
_API_REFRESH_ENCRYPTED = "Y5zVhB4c...（AES加密后的base64）"

# === 内置解密密钥（16字节，分两半存储防strings提取） ===
_KEY_PART1 = b'\x3a\x7f\x2c\x91\xe4\xb8\x55\x0d'
_KEY_PART2 = b'\xc6\xd2\x88\xfe\x17\xa3\x4b\x69'

def _get_aes_key() -> bytes:
    return _KEY_PART1 + _KEY_PART2

def _decrypt(encrypted_b64: str) -> str:
    """AES-256-EAX解密"""
    key = _get_aes_key()
    raw = base64.b64decode(encrypted_b64)
    nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode()

def get_public_key() -> str:
    return _decrypt(_PUBLIC_KEY_ENCRYPTED)

def get_api_url(endpoint: str) -> str:
    mapping = {
        "login": _API_LOGIN_ENCRYPTED,
        "verify": _API_VERIFY_ENCRYPTED,
        "refresh": _API_REFRESH_ENCRYPTED,
    }
    return _decrypt(mapping[endpoint])
```

### 4.7 开发者加密工具

```python
# tools/encrypt_strings.py（开发者在本地运行，不打包）

from Crypto.Cipher import AES
import base64
import os

KEY = os.urandom(32)  # 生成后固定，手动复制到 strings.py

def encrypt(plaintext: str) -> str:
    cipher = AES.new(KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode())
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode()

# 使用
print("KEY:", KEY.hex())
print("PUBLIC_KEY:", encrypt("""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...
-----END PUBLIC KEY-----"""))
print("API_LOGIN:", encrypt("https://www.7tan.com/api/auth/login.php"))
```

### 4.8 构建流程

```
开发阶段：
  src/security/license_verify.py   ← 明码，可修改
  src/security/rsa_verify.py       ← 明码
  src/security/strings.py          ← 手动粘贴加密后的字符串

构建阶段（build.bat 中加入）：
  ① 运行 tools/encrypt_strings.py → 更新 strings.py
  ② Cython 编译：
     python setup_cython.py build_ext --inplace
     → 生成 license_verify.pyd
     → 生成 rsa_verify.pyd
     → 生成 safe_modify.pyd
  ③ 删除原始 .py 文件（移到备份目录）
  ④ PyInstaller 打包（包含 .pyd）
```

### 4.9 Cython 编译配置

```python
# setup_cython.py
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        [
            "src/security/license_verify.py",
            "src/security/rsa_verify.py",
            "src/security/safe_modify.py",
        ],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
    )
)
```

### 4.10 攻击者面临的挑战

| 攻击方式 | 为什么失败 |
|:--|:--|
| 直接看源码 | .pyd 是二进制，无法阅读 |
| 反编译 .pyd | Cython 编译的是机器码，不像 .pyc 可反编译 |
| `strings` 提取密钥 | 密钥分两半存储，非连续字节 |
| 修改公钥 | AES 加密存储，找到也改不了 |
| 跳过验证函数 | 多处调用，删不干净 |
| Hook Python 导入 | 验证在 C 级别执行 |

---

## 五、新手引导

### 5.1 流程概览

```
启动 → 登录（或试用3次）
         │
         ↓
    ① 欢迎页：告知需要自带 Key
         │
         ↓
    ② 推荐页：推荐 DeepSeek + 两个模型对比
         │
         ↓
    ③ 填 Key：引导获取 + 填写（或跳过试用3次）
         │
         ↓
    进入主界面 ✅
```

### 5.2 第一步：欢迎页

```
┌────────────────────────────────────────────┐
│          🦊  欢迎使用 7Tan                 │
│                                            │
│          ┌──────────┐                      │
│          │ 7Tan LOGO │                      │
│          └──────────┘                      │
│                                            │
│     7Tan 是一款 AI 游戏开发助手             │
│     写代码 · 分析游戏 · 发布资源            │
│                                            │
│     ⚠️ 7Tan 不内置 AI 模型                 │
│     你需要提供自己的 API Key 才能使用       │
│                                            │
│           [开始设置 →]                     │
└────────────────────────────────────────────┘
```

### 5.3 第二步：推荐 DeepSeek

```
┌────────────────────────────────────────────┐
│  🧠 选择你的 AI 模型                       │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │  ⭐ 推荐                              │  │
│  │                                      │  │
│  │  我们建议使用 DeepSeek                │  │
│  │  目前性价比最高、最好用的国产 AI       │  │
│  │                                      │  │
│  │  💰 价格参考                          │  │
│  │     简单聊一句        ≈ 1-3 分钱     │  │
│  │     让 AI 写段代码    ≈ 1-3 毛钱     │  │
│  │     重度使用一整天    ≈ 10-30 元     │  │
│  │     用多少扣多少，1 元起充            │  │
│  │                                      │  │
│  │  🇨🇳 中文最强                          │  │
│  │  ⚡ 稳定可靠、不卡顿、不限频          │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ 📋 推荐模型：                        │  │
│  │                                      │  │
│  │ 🥇 deepseek-flash                    │  │
│  │    主力模型 · 日常首选                │  │
│  │    适合：写作、分析、日常问答         │  │
│  │                                      │  │
│  │ 🥈 deepseek-v4-flash                 │  │
│  │    极速响应 · 更便宜                 │  │
│  │    适合：日常聊天、快速问答、翻译     │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  [🔗 打开 DeepSeek 官网注册充值]           │
│  [📺 查看获取 Key 教程]                    │
│                                            │
│  [下一步 →]                               │
└────────────────────────────────────────────┘
```

### 5.4 第三步：填写 Key

```
┌────────────────────────────────────────────┐
│  🔑 填入你的 API Key                       │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ DeepSeek API Key                     │  │
│  │ sk-________________________________  │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  📌 Key 获取步骤：                         │
│    ① 打开 platform.deepseek.com           │
│    ② 注册 → 充值（1元起）                  │
│    ③ API Keys → 创建 → 复制               │
│                                            │
│  ⚠️ 提示：                                │
│  · Key 只保存在你的本地电脑                │
│  · 7Tan 不会上传、不会收集你的 Key         │
│  · 你可以随时在设置中更换                  │
│                                            │
│  [🎁 先试用 3 次（无需 Key）]              │
│  [完成设置 →]                              │
└────────────────────────────────────────────┘
```

### 5.5 设置页中的模型切换

```
┌────────────────────────────────────────────┐
│  ⚙️ AI 模型设置                           │
│                                            │
│  API Key：sk-****a8b3         [更换]       │
│                                            │
│  当前模型：                                │
│  ┌──────────────────────────────────────┐  │
│  │ ● deepseek-flash          推荐 🥇   │  │
│  │   主力模型 · 日常首选                │  │
│  │                                      │  │
│  │ ○ deepseek-v4-flash      推荐 🥈    │  │
│  │   极速便宜 · 日常对话/翻译           │  │
│  │                                      │  │
│  │ ○ 自定义模型                         │  │
│  │   ┌────────────────────────────┐     │  │
│  │   │ 模型名称：                 │     │  │
│  │   └────────────────────────────┘     │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  余额不足？[🔗 去 DeepSeek 充值]           │
└────────────────────────────────────────────┘
```

### 5.6 不内置 AI Key 充值

**7Tan 不做 AI 模型充值中转站**。用户自行去 DeepSeek 官网搞定。登录界面不出现任何 AI Key 购买入口。

---

## 六、安全修改机制（专业版核心功能）

### 6.1 三层防护体系

```
修改前 → 备份 + 语法检查
修改后 → 启动验证 + 看门狗
启动失败 → 自动回滚 + 安全模式
```

### 6.2 权限门控

```
用户要求修改文件
       │
       ├── 目标在 安装目录内？
       │   ├── YES → 检查授权
       │   │   ├── pro + 未过期 → ✅ 允许
       │   │   └── basic       → ❌ 拒绝
       │   └── NO  → ✅ 允许（游戏项目等）
       │
       └── 写入成功后 → 提示重启生效
```

### 6.3 门控代码

```python
# src/security/safe_modify.py

from pathlib import Path
from .license_verify import verify_license

_INSTALL_DIR = Path(__file__).resolve().parent.parent.parent

def can_modify_self(token_str: str) -> bool:
    """检查是否有权限修改软件自身"""
    try:
        result = verify_license(token_str)
        return result["level"] == "pro"
    except Exception:
        return False

def check_write_permission(target_path: str, token_str: str) -> bool:
    """写入文件前检查权限"""
    target = Path(target_path).resolve()
    if _INSTALL_DIR not in target.parents:
        return True  # 安装目录外的文件，允许
    return can_modify_self(token_str)
```

---

## 七、修改前防护（第一层）

### 7.1 pre_modify_check

```python
# src/security/safe_modify.py（编译成 .pyd）

def pre_modify_check(filepath: str, new_content: str) -> bool:
    """
    修改前的安全检查。任一失败则拒绝修改。
    """
    fp = Path(filepath)
    
    # === 检查1：Python语法检查 ===
    if fp.suffix == ".py":
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            raise ModifyRejected(f"语法错误，拒绝修改：{e}")
    
    # === 检查2：关键文件保护 ===
    PROTECTED = ("main.py", "safe_modify.pyd", "license_verify.pyd",
                 "rsa_verify.pyd", "strings.py")
    if fp.name in PROTECTED:
        raise ModifyRejected(
            f"核心文件 {fp.name} 不允许直接修改，请通过专用接口"
        )
    
    # === 检查3：自动备份 ===
    create_backup(str(fp))
    
    # === 检查4：文件大小合理性 ===
    if len(new_content) < 10 and fp.stat().st_size > 1000:
        raise ModifyRejected("新内容过短，疑似误删，拒绝修改")
    
    return True

class ModifyRejected(Exception):
    pass
```

### 7.2 自动备份

```python
BACKUP_DIR = Path("data/backups")
MAX_BACKUPS = 5  # 每个文件最多保留5个版本

def create_backup(filepath: str):
    """创建备份，保留最近5个版本"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    fp = Path(filepath)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{fp.name}.{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    
    shutil.copy2(fp, backup_path)
    
    # 更新索引
    index = _load_index()
    key = str(fp.resolve())
    if key not in index:
        index[key] = []
    index[key].append(backup_name)
    
    # 只保留最近5个
    while len(index[key]) > MAX_BACKUPS:
        old = index[key].pop(0)
        (BACKUP_DIR / old).unlink(missing_ok=True)
    
    _save_index(index)
```

---

## 八、启动验证（第二层）

### 8.1 启动自检

```python
# main.py 最开头，任何模块导入之前

import sys
from pathlib import Path

def startup_self_check():
    """启动自检，不通过则自动回滚"""
    
    # ① 检查关键文件存在
    required_files = [
        "src/security/license_verify.pyd",
        "src/security/rsa_verify.pyd",
        "src/security/safe_modify.pyd",
        "src/security/strings.py",
    ]
    for f in required_files:
        if not Path(f).exists():
            return False, f"核心文件缺失: {f}"
    
    # ② 尝试导入关键模块
    try:
        from src.security.license_verify import verify_license
        from src.security.safe_modify import pre_modify_check
    except ImportError as e:
        return False, f"核心模块导入失败: {e}"
    
    # ③ 检查 main.py 自身语法完整性
    try:
        with open(__file__, "r", encoding="utf-8") as f:
            compile(f.read(), __file__, "exec")
    except SyntaxError as e:
        return False, f"main.py 语法错误: {e}"
    
    return True, "OK"
```

### 8.2 自动回滚

```python
def attempt_recovery():
    """尝试从备份恢复最近版本"""
    from src.security.safe_modify import restore_latest_backup
    restored = restore_latest_backup()
    if restored:
        print(f"[恢复] 已回滚 {len(restored)} 个文件到上次正常版本")
    return restored
```

### 8.3 实际启动流程

```python
if __name__ == "__main__":
    ok, msg = startup_self_check()
    
    if not ok:
        print(f"[启动失败] {msg}")
        restored = attempt_recovery()
        
        if restored:
            # 弹窗告知用户后重启
            import tkinter.messagebox as mb
            mb.showwarning(
                "7Tan - 自动修复",
                f"检测到以下文件修改导致启动失败：\n{msg}\n\n"
                f"已自动回滚 {len(restored)} 个文件。\n"
                "点击确定后重新启动。"
            )
            subprocess.Popen(
                [sys.executable] + sys.argv,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            sys.exit(0)
        else:
            import tkinter.messagebox as mb
            mb.showerror(
                "7Tan - 启动失败",
                f"启动失败且无法自动修复：\n{msg}\n\n"
                "请尝试：\n"
                "1. 按住 Shift 双击启动 → 安全模式\n"
                "2. 重新安装软件"
            )
            sys.exit(1)
    
    # 启动通过，正常进入
    main()
```

---

## 九、安全模式（第三层——最后救命稻草）

### 9.1 触发方式

- **按住 Shift 键**双击启动 → 进入安全模式
- 或命令行 `7tan.exe --safe-mode`

### 9.2 安全模式行为

```python
def is_safe_mode():
    """检测是否按住 Shift 启动"""
    try:
        import ctypes
        return (
            ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000
            or "--safe-mode" in sys.argv
        )
    except:
        return "--safe-mode" in sys.argv


if is_safe_mode():
    print("[安全模式] 跳过所有用户修改，加载原始版本")
    from src.security.safe_modify import restore_all_from_backup
    restore_all_from_backup()
    
    import tkinter.messagebox as mb
    mb.showinfo(
        "7Tan - 安全模式",
        "已进入安全模式。\n"
        "所有用户修改已回滚到原始版本。\n"
        "你可以重新开始修改。"
    )
```

### 9.3 完整流程图

```
用户："帮我把背景色改成深蓝"
  │
  ▼
AI 生成新代码
  │
  ▼
pre_modify_check(filepath, new_content)
  ├── ast.parse() 语法检查 ──失败──→ ❌ 拒绝，告知用户原因
  ├── 关键文件保护检查 ──命中──→ ❌ 拒绝
  └── 自动备份原文件 ──成功──→ ✅
  │
  ▼
write_file() 写入新内容
  │
  ▼
提示用户："修改完成，需要重启生效。[立即重启] [稍后]"
  │
  ▼
用户点击 [立即重启]
  │
  ▼
软件重启 → startup_self_check()
  ├── ✅ 通过 → 正常进入主界面 🎉
  └── ❌ 失败 → attempt_recovery()
                ├── ✅ 回滚成功 → 弹窗告知 → 重新启动
                └── ❌ 回滚失败 → 提示安全模式
                                    │
                                    ▼
                               Shift双击启动
                                    │
                                    ▼
                              恢复全部原始文件 ✅
```

---

## 十、其他调整

### 10.1 删除 img.7tan.cn 管理后台入口

登录界面不再显示管理后台登录入口。用户可配置自己的网站地址。

### 10.2 subprocess 黑窗口修复

`main.py` 全局 monkey patch，所有 `subprocess.run/Popen/call/check_call/check_output` 自动加上 `CREATE_NO_WINDOW`：

```python
# main.py 第 28-52 行
import subprocess as _sp

_orig_run = _sp.run
_orig_popen = _sp.Popen

def _patched_run(*args, **kwargs):
    kwargs.setdefault("encoding", "utf-8")
    if "creationflags" not in kwargs:
        kwargs["creationflags"] = _sp.CREATE_NO_WINDOW
    else:
        kwargs["creationflags"] |= _sp.CREATE_NO_WINDOW
    return _orig_run(*args, **kwargs)

def _patched_popen(*args, **kwargs):
    if "creationflags" not in kwargs:
        kwargs["creationflags"] = _sp.CREATE_NO_WINDOW
    else:
        kwargs["creationflags"] |= _sp.CREATE_NO_WINDOW
    return _orig_popen(*args, **kwargs)

_sp.run = _patched_run
_sp.Popen = _patched_popen
# call/check_call/check_output 底层用 Popen，自动继承
```

### 10.3 用户可配置网站地址

专业版用户可修改 API 端点指向自己的服务器（通过设置界面配置，存储在加密的本地配置中）。

---

## 十一、文件变更清单

### 11.1 新增文件

```
docs/
└── architecture.md              ← 本文档

src/security/
├── __init__.py                  ← 模块初始化
├── license_verify.py            ← 授权验证（构建时Cython编译→.pyd）
├── rsa_verify.py                ← RSA验签（构建时Cython编译→.pyd）
├── safe_modify.py               ← 安全修改门控（构建时Cython编译→.pyd）
├── strings.py                   ← 敏感字符串（AES加密存储）
└── public_key.pem               ← RSA公钥

tools/
└── encrypt_strings.py           ← 开发者加密工具（不打包）

setup_cython.py                  ← Cython编译配置

data/backups/                    ← 自动备份目录（运行时创建）
└── index.json                   ← 备份索引
```

### 11.2 修改文件

| 文件 | 变更内容 |
|:--|:--|
| `main.py` | ① monkey patch subprocess ② 启动自检 + 回滚逻辑 ③ 安全模式入口 |
| `build.bat` | 加入 Cython 编译步骤 → PyInstaller 打包 |
| 登录界面 | 用户名或手机号 / 30天记住 / 删除AI Key购买入口 |
| 新手引导 | 新增 DeepSeek 推荐流程 |
| `ll_useregs` 表 | 新增 pro_expires、pro_activated 字段 |

### 11.3 API 新增（7tan.com）

```
api/auth/login.php       ← 登录接口
api/auth/verify.php      ← Token验证 + 会员状态
api/auth/refresh.php     ← 续费后刷新Token
```

---

## 十二、构建流程

```
① 运行 tools/encrypt_strings.py
   → 手动将加密后的字符串粘贴到 src/security/strings.py

② Cython 编译
   python setup_cython.py build_ext --inplace
   → 生成 license_verify.pyd, rsa_verify.pyd, safe_modify.pyd

③ 删除原始 .py（或移到 backup_src/）

④ PyInstaller 打包
   pyinstaller 7tan.spec
   → dist/7tan-editor/7tan.exe

⑤ 测试
   · 登录测试（用户名+手机号）
   · 离线Token验证
   · 安全修改 → 重启 → 自检 → 回滚
   · Shift安全模式
```

---

> 📌 本文档随开发进度持续更新。任何架构变更必须先更新本文档再实施。

---

## 十三、7tan.com 会员中心

### 13.1 概述

7tan.com 是配套网站，提供注册、登录、充值、购买专业版、查看会员状态等功能。客户端通过 API 与网站通信验证授权。

### 13.2 用户完整流程

```
新用户访问 7tan.com
    │
    ├── 注册（用户名/手机号/邮箱/密码）
    │
    └── 登录
          │
          ↓
     进入【个人中心】

个人中心功能：
    ├── 💰 账户充值（支付宝/微信）
    ├── ⭐ 购买专业版（200元/半年，支持余额支付或直接支付）
    ├── 📋 订单记录
    └── 👤 个人信息管理
```

### 13.3 数据库表设计

```sql
-- 用户表
CREATE TABLE users (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    username    VARCHAR(50) NOT NULL UNIQUE,
    phone       VARCHAR(20) DEFAULT NULL,
    email       VARCHAR(100) DEFAULT NULL,
    password    VARCHAR(255) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone),
    INDEX idx_email (email)
);

-- 账户余额
CREATE TABLE user_balance (
    user_id     INT PRIMARY KEY,
    balance     DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 充值记录
CREATE TABLE recharge_records (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    payment_method  VARCHAR(20) NOT NULL,
    trade_no        VARCHAR(64),
    status          TINYINT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    paid_at         DATETIME DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id),
    INDEX idx_trade (trade_no)
);

-- 专业版购买记录
CREATE TABLE pro_purchases (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT NOT NULL,
    months          INT NOT NULL DEFAULT 6,
    amount          DECIMAL(10,2) NOT NULL,
    pay_type        VARCHAR(20) NOT NULL,
    trade_no        VARCHAR(64),
    status          TINYINT DEFAULT 0,
    activated_at    DATETIME DEFAULT NULL,
    expires_at      DATETIME DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id),
    INDEX idx_expires (expires_at)
);

-- Token 签发记录
CREATE TABLE auth_tokens (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    user_id     INT NOT NULL,
    jti         VARCHAR(64) NOT NULL UNIQUE,
    expires_at  DATETIME NOT NULL,
    revoked     TINYINT DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id)
);
```

### 13.4 页面结构

```
7tan.com/
├── /                             首页
├── /register                     注册页
├── /login                        登录页
├── /user/                        个人中心（需登录）
│   ├── /user/index               概览（余额、会员状态、到期时间）
│   ├── /user/recharge            充值页面
│   ├── /user/pro                 购买专业版页面
│   ├── /user/orders              订单记录
│   └── /user/profile             个人信息
├── /api/auth/                    认证 API
│   ├── login.php                 登录
│   ├── register.php              注册
│   ├── verify.php                验证Token+会员状态
│   ├── refresh.php               刷新Token
│   └── logout.php                登出
├── /api/pay/                     支付 API
│   ├── recharge.php              创建充值订单
│   ├── notify.php                支付回调
│   └── query.php                 查询支付结果
└── /api/pro/                     专业版 API
    ├── purchase.php              购买专业版
    └── status.php                查询专业版状态
```

### 13.5 核心 API 接口

#### 登录

```
POST /api/auth/login.php
请求：  { "account": "用户名或手机号", "password": "密码" }
响应：  { "code": 0, "data": { "token": "eyJ...", "user":
          { "uid":10001, "username":"test", "level":"pro",
            "balance":15.50, "pro_expires":"2026-06-15 12:00:00" } } }
```

#### 注册

```
POST /api/auth/register.php
请求：  { "username":"test", "phone":"13800138000", "password":"xxx" }
响应：  { "code": 0, "data": { "uid": 10001, "message": "注册成功" } }
```

#### 验证Token

```
GET /api/auth/verify.php
响应：  { "code": 0, "data": { "uid":10001, "level":"pro",
          "balance":15.50, "pro_expires":"2026-06-15 12:00:00" } }
```

#### 创建充值订单

```
POST /api/pay/recharge.php
请求：  { "amount": 10.00, "method": "alipay" }
响应：  { "code": 0, "data": { "order_no":"R20260115001",
          "pay_url":"..." } }
```

#### 支付回调

```
POST /api/pay/notify.php
支付宝/微信异步通知 → 验签 → 更新余额 → 更新订单状态
```

#### 购买专业版

```
POST /api/pro/purchase.php
请求：  { "months": 6, "pay_type": "balance" }

余额支付流程：
① 验证余额 >= 200 元
② 扣减余额
③ 创建 pro_purchases 记录，status=已激活
④ 更新用户 level="pro"，pro_expires 延长
⑤ 签发新 JWT 返回客户端

响应：  { "code": 0, "data": { "new_token":"eyJ...", "level":"pro",
          "pro_expires":"2026-12-15 12:00:00", "balance":5.50 } }
```

#### 刷新Token

```
POST /api/auth/refresh.php
响应：  { "code": 0, "data": { "new_token":"eyJ...", "level":"pro",
          "pro_expires":"2026-12-15 12:00:00" } }
```

### 13.6 支付集成方案

```
用户在 7tan.com 点击充值
    │
    ├── 选择金额：10 / 20 / 50 / 100 / 自定义
    ├── 选择方式：支付宝 / 微信
    │
    ↓
后端创建订单 → 调用支付宝/微信下单接口
    │
    ↓
前端展示二维码或跳转支付
    │
    ↓
用户完成支付
    │
    ↓
支付宝/微信 → POST /api/pay/notify.php
    ├── 验签通过 → 更新余额 + 订单状态
    └── 验签失败 → 记录日志，拒绝
    │
    ↓
前端轮询 /api/pay/query.php → 显示充值成功
```

### 13.7 购买专业版流程

```
用户进入个人中心 → 点击 [购买专业版]
    │
    ├── 方式一：余额支付（余额足够时）
    │   ├── 确认订单：200元 / 6个月
    │   ├── 点击 [确认支付]
    │   ├── 后端扣减余额 → 激活专业版 → 签发新Token
    │   └── 完成 ✅
    │
    └── 方式二：直接支付（余额不足时）
        ├── 确认订单：200元 / 6个月
        ├── 选择支付宝/微信
        ├── 跳转支付
        ├── 支付成功回调 → 激活专业版
        └── 完成 ✅

激活后：
    ├── 网站：会员状态立即更新
    └── 客户端：打开软件 → [刷新状态] → 调用 refresh.php → 获取新Token
```

### 13.8 会员到期处理

| 阶段 | 处理 |
|:--|:--|
| 到期前 7 天 | 个人中心显示提醒；客户端登录时提示 |
| 到期当天 | level 自动降为 "basic"；下次刷新Token后权限降级 |
| 到期前续费 | 从当前到期日延长（不损失剩余天数） |
| 到期后续费 | 从购买日重新计算 |
| 多次购买 | 可叠加（购买12个月=200×2=400元，或设年费优惠价） |

### 13.9 安全措施

| 措施 | 说明 |
|:--|:--|
| 密码加密 | bcrypt hash，永不明文存储 |
| JWT签名 | RSA 签名，防篡改 |
| 支付验签 | 支付宝/微信回调验签，防伪造通知 |
| 余额操作 | 数据库事务，防并发扣款 |
| Token吊销 | 支持服务端吊销，防泄露 |
| 登录保护 | 连续失败5次锁定15分钟 |
| HTTPS | 全站强制 HTTPS |
| SQL注入 | 所有查询参数化 |
| XSS | 输出转义 + CSP 头 |

---

## 十四、整体架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    7Tan 整体架构                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌──────────────┐         ┌──────────────────────┐    │
│   │  7tan.com    │  HTTPS  │   7Tan 客户端        │    │
│   │              │◄───────►│                      │    │
│   │ · 注册/登录  │   API   │ · AI对话/写代码      │    │
│   │ · 充值      │         │ · 游戏分析/发布      │    │
│   │ · 购买专业版 │         │ · 开发运维工具       │    │
│   │ · 个人中心   │         │ · 自我修改(专业版)   │    │
│   └──────┬───────┘         └──────────┬───────────┘    │
│          │                            │                 │
│          │ MySQL                      │ SQLite          │
│          ▼                            ▼                 │
│   ┌──────────────┐         ┌──────────────────────┐    │
│   │ 7tan.com DB  │         │ 本地数据库            │    │
│   │ · users      │         │ · 游戏资源            │    │
│   │ · balance    │         │ · 任务日志            │    │
│   │ · pro_purch  │         │ · 配置缓存            │    │
│   │ · auth_token │         │ · 代码片段            │    │
│   └──────────────┘         └──────────────────────┘    │
│                                                         │
│   第三方服务：                                           │
│   · 支付宝/微信支付（充值/购买专业版）                   │
│   · DeepSeek API（AI模型）                              │
│   · 云存储 OSS（游戏包）                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

> 📌 本文档随开发进度持续更新。任何架构变更必须先更新本文档再实施。

```
