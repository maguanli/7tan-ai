# 🤖 七坛 QQ 机器人

基于 **NoneBot2 + OneBot v11** 协议，接入 DeepSeek AI。

---

## 🚀 快速开始（3步）

### 第1步：安装 NapCatQQ（OneBot 客户端）

NapCatQQ 是连接 QQ 和机器人的桥梁。

1. 下载 NapCatQQ：https://github.com/NapNeko/NapCatQQ/releases
2. 解压到任意目录，双击 `napcat.bat` 启动
3. 扫码登录你的机器人 QQ 号
4. NapCatQQ 默认会开启 WebSocket 服务在 `ws://127.0.0.1:3001`

> 💡 **替代方案**: 也可以用 **LLOneBot**（LiteLoaderQQNT 插件）

---

### 第2步：配置 NapCatQQ 反向WS

在 NapCatQQ 的 WebUI 中（默认 http://127.0.0.1:6099）：

1. 进入「网络设置」
2. 添加「反向 WebSocket」地址：`ws://127.0.0.1:8080/onebot/v11/ws`
3. 保存并重启 NapCatQQ

---

### 第3步：启动机器人

```bash
cd qqbot
start.bat
```

或手动：
```bash
pip install -r requirements.txt
python bot.py
```

看到 `🤖 七坛 QQ 机器人` 启动画面就成功了！

---

## 📋 功能

| 命令 | 说明 |
|------|------|
| `/hello` | 打招呼 |
| `/帮助` | 查看菜单 |
| `/状态` | 系统状态 |
| `/chat xxx` | AI聊天 |
| `/搜游戏 xxx` | 搜索游戏 |
| @机器人 xxx | 自动AI对话 |

---

## ⚙️ 配置

编辑 `.env` 文件：
- `SUPERUSERS` — 管理员QQ号
- `NICKNAME` — 机器人昵称

API Key 自动从系统环境变量读取（无需配置）。

---

## 🏗️ 架构

```
你的QQ号
    ↓
NapCatQQ (OneBot 服务端, ws://127.0.0.1:3001)
    ↓ WebSocket
NoneBot2 (机器人框架, ws://127.0.0.1:8080)
    ↓
DeepSeek API (AI对话)
七坛数据库 (游戏搜索)
```
