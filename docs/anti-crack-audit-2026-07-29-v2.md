# 7Tan 软件防破解审计报告（v2 修订版）

- **审计日期**: 2026-07-29
- **审计对象**: D:\7tan\7tanAI（源码）+ dist\7tan-editor（发布构建）
- **v2 修订说明**: 基于正确的商业模式重评估（基础版=全部功能，PRO=全部功能+自改进；AI 模型走用户自己的 Key）
- **校正后评分**: **55 / 100（C+ 级）** — 授权系统对正版用户不健康，但破解的实际获利很小

---

## 商业模式确认

| 版本 | 功能 | 付费驱动力 |
|---|---|---|
| 基础版 | 全部功能（AI 生成/爬取/改写/发布/插件/调度） | 免费使用 |
| 专业版（PRO） | 全部功能 + **对软件自身进行 AI 驱动的修改升级进化** | 自改进能力 |

关键前提：
- AI 模型调用走用户自己的 API Key，不走 7tan.com 服务器代理
- 基础版已经没有任何功能缩水，PRO 的差异化价值集中在"自改进"这一项

**在此模型下，防破解的核心目标不是防"盗用全功能"（全功能本来就免费），而是：**
1. 确保付费 PRO 用户的自改进能力正常可用（当前对正版用户是坏的）
2. 防止未付费用户使用自改进（当前确实也未生效，但因为公钥缺失，fail-closed）
3. 防范代码被反编译/篡改后用于二次分发或内嵌恶意代码

---

## 一、结论先行

| 维度 | 现状 | 评分 | 说明 |
|---|---|---|---|
| 授权验证（License） | ❌ 公钥为空，验签从未执行；PRO 自改进对正版用户不可用 | 5/20 | 坏在伤了付费用户，不是坏在防不住破解 |
| 代码保护（反逆向） | ❌ Cython 从未生效，发布版全部 .pyc 可提取反编译 | 10/20 | 对白嫖威胁有限，但防二次篡改分发需加强 |
| 自身安全（防篡改注入） | ⚠️ HMAC 清单存在但未接入启动；本地 API 免鉴权 | 8/20 | 篡改 exe 无告警，terminal API 有 RCE 风险 |
| 令牌体系（Auth 完整性） | ⚠️ 设计正确但执行断链；token 机器绑定有效 | 17/20 | 防"分享"有效，修复断链后可达满分 |
| 敏感信息管理 | ✅ git 管理规范，历史干净；⚠️ dist 配置有小瑕疵 | 10/15 | 总体良好 |
| 试用限制 | ❌ 删文件即重置 | 5/5 | 基础版全功能免费，试用限制基本无意义 |
| **合计** | | **55/100** | |

**一句话结论：当前发布版确实可以被"零逆向"伪造 PRO，但破解者拿到的 PRO 自改进能力，在你当前商业模式下实际获利极低——因为模型 API 走用户自己的 Key，且自改进本身就是 AI 驱动的一个辅助能力，不是一个"内容生成"类高消费资源。真正受影响的是付费 PRO 用户——因公钥缺失，他们的核心权限目前实际上无法使用。**

---

## 二、PoC 实锤（已在开发机验证，与原报告一致）

| # | 验证项 | 结果 | 威胁等级（修订后） |
|---|---|---|---|
| PoC-1 | 调用软件自身 `token_store._encrypt()` 伪造 `{"level":"pro"}`，再用 `_decrypt()` 解回 | ✅ 加解密完全自洽 | P1 — 破解获得的自改进能力价值有限 |
| PoC-2 | 发布配置下 `verify_license('a.b.c')` | ❌ 抛 `LicenseInvalid: 公钥缺失` | P0 — 正版 PRO 用户的自改进不可用 |
| PoC-3 | 试用计数器 `data/auth/trial.dat` | 删除即恢复 3 次 | P3 — 基础版全功能免费，试用于是无意义 |
| PoC-4 | 手工解析 exe 内嵌 PYZ 归档 | 4232 个模块全部可提取 | P1 — 防二次分发/篡改需要，但非紧急 |

---

## 三、核心发现

### P0 — 正版 PRO 用户的自改进能力不工作

这是当前最大的真实风险：**付费用户付了钱，但拿不到他们唯一买的东西。**

攻击链（与 v1 相同，但影响方向和紧迫性完全不同）：

```
strings.py 发布版 public_key = ""     ← 空占位符
    ↓
verify_license() 永远抛 LicenseInvalid
    ↓
can_modify_self() 永远返回 False      ← 自改进入口
    ↓
正版 PRO 用户登录成功后也无法触发自改进
```

涉及文件与修复点：
- `tools/encrypt_strings.py` → 未被用于生成公钥密文
- `src/security/strings.py:38` → `_STORE["public_key"] = ""` 仍为占位符
- `src/security/safe_modify.py:255-267` → `can_modify_self()` 因验签失败永远返回 False
- `src/ui/pro_status_widget.py:172-185` → 验签失败被 `pass` 绕过，UI 显示不反映真实授权状态

**修复目标：让付费 PRO 用户的自改进能正常工作，同时保持未付费用户无法使用。**

### P1-1 代码保护缺失 → 被篡改二次分发的风险

- Cython 编译（`setup_cython.py`）从未进入发布构建，9 个 security 模块全部以 .pyc 形式随 exe 发布，pyinstxtractor + pycdc 可反编译
- UPX 一层可以 `upx -d` 直接脱掉，无实质作用
- 无代码签名（`codesign_identity=None`），无法阻止恶意第三方修改 exe 后重新分发
- `startup_self_check()` 在 frozen 模式下跳过所有实质性检查 → 篡改版 exe 无自检能力

**威胁不是破解→白嫖 PRO（获利低），而是：有人解包→插入代码→重新发布，打着"7Tan 免费版"的旗号传播后门/挖矿/勒索软件，损害你的品牌声誉。**

### P1-2 本地 API 安全隐患（篡改辅助 + 独立 RCE 风险）

`src/web/server.py` → FastAPI 127.0.0.1:9800，本地请求免鉴权，含 `api_terminal.py`（`subprocess.Popen` 任意命令执行）。

- 本机任何进程可直接调用命令执行端点
- 浏览器恶意页面可通过 CSRF 请求 127.0.0.1:9800 执行命令
- 篡改版 exe 的作者可通过此端点更隐蔽地注入载荷

### P2 — 其他小问题

| 项 | 状态 | 说明 |
|---|---|---|
| 旧 DeepSeek Key | ⚠️ | .env 确认"旧 Key 已泄露"——请确认已在后台吊销 |
| dist/config.yaml | ⚠️ | 含绝对路径 `D:\7tan\7tanAI\data` 和 `username: admin` |
| 插件清单 | ⚠️ | 指向 GitHub raw URL，无签名校验 |
| `run_integrity()` | 🐛 | 引用不存在的 `checker._report` — AttributeError bug |
| git 安全 | ✅ | .gitignore 正确，历史无 key 残留 |
| token 机器绑定 | ✅ | 防"分享 PRO 账号"有效，换机自动失效 |

---

## 四、加固路线（按修正后的优先级）

### P0 — 让付费用户的自改进正常工作（1 天内）

1. **填入公钥**：运行 `tools/encrypt_strings.py` —— 输入服务器 RSA 公钥 + API 端点，更新 `strings.py`，重建发布包
2. **修复 trust 链**：`pro_status_widget` 中验签失败必须降级（删除 "except LicenseError: pass"），同时需要在验签失败时给出具体原因（公钥缺失 vs 令牌过期 vs 签名无效）帮助正版用户排查
3. **验证修复**：构建后确认以下断言通过：
   - `can_modify_self(valid_pro_token) → True`
   - `can_modify_self(invalid_token) → False`
   - `can_modify_self("") → False`

### P1 — 防二次分发/篡改（发布前）

4. **让 Cython 真正生效**：编译清单补上 strings.py、token_store.py、trial_store.py、integrity.py、auth_client.py；build.bat 加后置断言（PYZ 内不得含 `src.security.*` 源码）；清理 `startup_self_check()` 为 frozen 模式也必须执行实质检查
5. **完整性校验接入启动**：启动时跑 integrity.check_all()，失败拒绝运行；HMAC 密钥改为构建期注入随机值；修复 `run_integrity()` 的 bug
6. **本地 API 收口**：启动时生成随机端口 + 一次性 token；GUI 请求头携带；terminal 端点默认关闭
7. **exe 加代码签名**：OV 证书，阻止篡改后的 exe 被 SmartScreen 识别为"未知发布者"

### P2 — 粉饰（有时间再做）

8. 反调试/反注入（IsDebuggerPresent 等）
9. 发布前清理 dist 配置（去除绝对路径和硬编码用户名）
10. 插件清单 RSA 签名校验
11. **建立发布检查清单**纳入 build.bat 最后一步强制卡点

---

## 五、最重要的一句话

你的软件**不是防护不够，是授权系统坏了导致付费用户的权限没发出去**。

修好之后，就算有人伪造 PRO，拿到的也是一个依赖他自己的 API Key 跑的自改进能力——这不是一个值得专门破解的目标。与其花时间跟破解者斗，不如花一天修好授权管好正版用户体验。
