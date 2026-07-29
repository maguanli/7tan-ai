# 7Tan 软件防破解全面审计报告

- **审计日期**: 2026-07-29
- **审计对象**: D:\7tan\7tanAI（源码）+ dist\7tan-editor（发布构建）
- **总体评分**: **30 / 100（D 级）** — 设计方案有 70 分水平，但落地执行存在致命断链，当前发布版可被"零逆向"破解

---

## 一、结论先行

| 维度 | 现状 | 评分 |
|---|---|---|
| 授权验证（License） | ❌ 公钥为空，验签被永久跳过，本地存储字段被无条件信任 | 5/25 |
| 代码保护（反逆向） | ❌ Cython 未实际生效，发布版全部为可提取的 .pyc 字节码 | 8/25 |
| 完整性/防篡改 | ⚠️ 有 HMAC 清单机制但未接入启动流程，密钥硬编码 | 6/20 |
| 试用限制 | ❌ 删除一个文件即重置 | 2/15 |
| 敏感信息管理 | ✅ .gitignore 正确、git 历史干净；⚠️ dist 配置含开发机绝对路径 | 9/15 |
| **合计** | | **30/100** |

**一句话结论：当前发布版不需要任何逆向技术即可破解——破解者在本机用软件自带的加密逻辑伪造一个 `token.dat` 即显示 PRO；用公开工具 pyinstxtractor 可完整解包全部源码字节码。**

---

## 二、PoC 实锤（已在开发机验证）

| # | 验证项 | 结果 |
|---|---|---|
| PoC-1 | 调用软件自身 `token_store._encrypt()` 伪造 `{"level":"pro","pro_expires":9999999999}`，再用 `_decrypt()` 解回 | ✅ 加解密完全自洽，伪造 token 可行 |
| PoC-2 | 调用发布配置下的 `verify_license('a.b.c')` | ❌ 抛 `LicenseInvalid: 系统配置错误：公钥缺失` — 本地验签从未生效 |
| PoC-3 | 试用计数器 `data/auth/trial.dat` | 删除文件即恢复 3 次试用（XOR 密钥也在二进制内，形同明文） |
| PoC-4 | 手工解析 `7tan-editor.exe` 内嵌 PYZ 归档 | 4232 个模块全部可提取，含完整 `src.security.*` 字节码（marshal code object） |

---

## 三、核心发现（按攻击路径排序）

### P0-1 授权体系被架空（三处缺陷叠加，缺一不可修）

攻击链：

```
strings.py 发布版 public_key = ""（空占位符，encrypt_strings.py 从未填入公钥）
    ↓
verify_license() 永远抛 LicenseInvalid
    ↓
pro_status_widget._update_display() 中 except LicenseError: pass
（注释明写"只升级不降级"）
    ↓
UI 的 PRO 状态完全由 token.dat 里的 level 字段决定
    ↓
token.dat 加密密钥 = PBKDF2(主机名+架构+MAC+主板序列号, 内置盐)
——全部输入在本机可复现，破解者用软件自己的代码 3 行伪造 PRO
```

涉及文件：
- `src/security/strings.py:38` — `_STORE["public_key"] = ""` 发布版未替换
- `src/ui/pro_status_widget.py:172-185` — 优先信任存储的 level，验签失败静默跳过
- `src/security/token_store.py:43-78` — 机器绑定密钥可本机复现（防"分享"有效，防"伪造"无效）

### P0-2 功能门禁形同虚设

全代码库 grep 结果：**主程序 `src/ui/app.py` 中没有任何按 level 的功能门禁**。唯一的两处真实门禁：

| 位置 | 门禁内容 | 现状 |
|---|---|---|
| `login_dialog.py:465` | 未登录试用 3 次 | 删 trial.dat 即重置（见 P0-3） |
| `safe_modify.py:266 can_modify_self()` | 自改进需 PRO | 因公钥缺失**永远返回 False** — 正版 PRO 用户也用不了，功能对正版也是坏的 |

即：当前"PRO"实际上只是一个侧边栏徽章，没有锁住任何功能。从防盗版角度这是"幸运"（破解者无利可图之外的动机低），但从商业化角度，PRO 用户付费后也没有得到任何差异化能力。

### P0-3 试用限制可秒重置

`src/security/trial_store.py`：XOR + base64 混淆，注释自称"仅防止记事本直接改数字"。实际上：
- 删文件 → `get_trials_left()` 返回 `MAX_TRIALS = 3`，无限循环
- 文件损坏 → 自动 `_reset_trials()` 重置为 3（把文件写成随机垃圾也算"损坏"）

### P1-1 发布构建无实质代码保护

实测 `dist/7tan-editor/7tan-editor.exe`（21.5MB）：

| 保护措施 | 设计 | 实际 |
|---|---|---|
| Cython 编译安全模块 | setup_cython.py 编译 3 个模块为 .pyd | ❌ 从未执行/未进入构建：PYZ 内 9 个 security 模块全部为 .pyc 字节码，且 strings.py/auth_client.py/token_store.py/trial_store.py/integrity.py **本就不在编译清单里** |
| PyInstaller | onedir + PYZ | ⚠️ pyinstxtractor 一键解包；Python 3.12 字节码可被 pycdc 反编译 |
| UPX | upx=True | ❌ 副作用为主：`upx -d` 一键还原，且增加杀软误报率 |
| 代码签名 | codesign_identity=None | ❌ 未签名，无法防二次打包冒充，SmartScreen 拦截 |

### P1-2 完整性校验未接入启动流程

- `main.py startup_self_check()`：frozen 模式下跳过 .pyd 存在性检查（①）和语法检查（③），只剩"能 import 就算过"
- `integrity.py` 的 HMAC 清单校验只在手动运行 `main.py integrity` 时执行，正常启动从不调用
- HMAC 密钥 `7tan_integrity_secret_v5` 硬编码在客户端，破解者可直接重签清单
- `main.py run_integrity()` 引用不存在的 `checker._report` 属性 → 该命令一跑就 AttributeError（连带 bug）
- 结论：篡改任何文件（包括替换成含后门的版本）启动时无任何告警

### P1-3 本地 API 攻击面（安全隐患 + 破解辅助通道）

`src/web/server.py`：FastAPI 监听 127.0.0.1:9800，**所有本地请求免鉴权**，且路由包含 `api_terminal.py`（`subprocess.Popen` 任意命令执行）。

风险：
1. 本机任何进程（含无admin权限的恶意软件）可直接调用命令执行端点
2. 浏览器恶意网页可通过 CSRF/DNS Rebinding 访问 127.0.0.1:9800（未校验 Origin/Host 头）→ 网页驱动本机 RCE
3. 破解者可绕过 GUI 直接调用 API 驱动全部功能，客户端任何门禁都无效

### P2 敏感信息与其他

| 项 | 状态 | 说明 |
|---|---|---|
| .env 是否进 git | ✅ 已排除 | .gitignore 正确，git 历史 grep `sk-` 无残留 |
| 旧 DeepSeek Key | ⚠️ 需确认 | .env 注释确认"旧 Key 已泄露"——**确认已在 DeepSeek 后台吊销** |
| dist/config.yaml | ⚠️ | 含开发机绝对路径 `D:\7tan\7tanAI\data` 和 `username: admin`；`${TANTAN_PASSWORD}` 依赖用户机器 .env，缺失时静默为空（功能 bug + 信息泄露） |
| .env TANTAN 凭据 | ⚠️ | admin/admin123 弱密码，若服务器后台真实使用需立即更换 |
| 插件清单 | ⚠️ | `plugins.remote_manifest_url` 指向 GitHub raw，未见签名校验，中间人/仓库被控可下发恶意插件 |
| API 端点加密 | ✅ 思路正确 | 但 AES 密钥与密文同文件，仅挡 strings 扫描，挡不住动态分析 |

---

## 四、加固路线（按优先级）

### P0 — 不做就等于裸奔（1 天内可完成）

1. **填入公钥**：运行 `tools/encrypt_strings.py` 生成 `public_key` 密文写入 strings.py，重建发布包
2. **修复 pro_status_widget 信任逻辑**：
   - level 判定必须以 `verify_license()` 验签通过为准
   - 验签失败/公钥缺失时必须**降级**（fail-closed），删除"只升级不降级"逻辑
   - token.dat 的 level 仅作为离线展示缓存，不作为授权依据
3. **让 Cython 真正生效**：
   - 编译清单补上 strings.py、token_store.py、trial_store.py、integrity.py、auth_client.py
   - build.bat 加构建断言：发布包 PYZ 内不得出现 `src.security.*` 的 Python 源码模块，否则构建失败
4. **试用计数防重置**：trial 状态与 token/机器指纹联动 + 多副本隐藏存储（注册表 + 多处文件互备），检测到副本不一致取最小值；更优方案是试用也必须登录，由服务端计数

### P1 — 商业化前必须完成

5. **价值功能服务端化**（根治）：把值得付费的能力（AI 代理额度、自改进下发、专属模型）放到 7tan.com 服务端，客户端只持短期 token + 定期在线刷新；本地只做"展示层"判断。客户端保护做到位只能提高门槛，服务端化才能根治
6. **完整性校验接入启动**：启动时校验核心文件哈希，失败拒绝运行；HMAC 密钥改为构建期注入的随机值（每次发布不同）；修复 `run_integrity()` 的 `_report` bug
7. **替换打包保护方案**：PyInstaller → PyArmor（推荐，带混淆+许可绑定）或 Nuitka（真编译）；exe 加 OV 代码签名
8. **本地 API 收口**：启动时生成随机端口 + 一次性 API token，GUI 请求头携带；校验 Origin/Host 头防浏览器 CSRF；terminal 端点默认关闭，设置中显式开启

### P2 — 纵深防御

9. 反调试/反注入：IsDebuggerPresent、检测 Frida/x64dbg/CE 进程、父进程校验
10. 发布前清理 dist 配置：去除绝对路径、内置用户名；日志对 token/key 脱敏
11. 插件清单 RSA 签名校验
12. 建立"发布检查清单"（公钥已填？.pyd 已编？签名已打？自检已开？）纳入 build.bat 强制卡点

---

## 五、评分预估

| 阶段 | 评分 | 说明 |
|---|---|---|
| 当前发布版 | **30/100（D）** | 零逆向可破 |
| 完成 P0 | ~60/100（C+） | 堵住伪造 token + 真实代码保护，破解需要专业逆向能力 |
| 完成 P0+P1 | ~78/100（B+） | 独立软件品类中的良好水平，破解成本高于购买成本 |
| 完成全部 | ~85/100（A-） | 配合服务端化，达到商业软件主流水位 |

> 注：纯客户端软件不存在 100 分。目标是让破解成本 >> 正版价格，并保护正版用户体验。
