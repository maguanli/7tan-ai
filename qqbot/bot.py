"""
七坛 QQ 机器人 - 基于 NoneBot2 + OneBot v11
============================================
用法:
  1. 先启动 NapCatQQ (OneBot 服务端)，登录QQ
  2. 再运行: python bot.py
  3. 或者双击 start.bat

NapCatQQ 下载: https://github.com/NapNeko/NapCatQQ/releases
"""

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11_Adapter

# 初始化 NoneBot
nonebot.init(
    command_start={"/", "！", "／"},  # 命令前缀
    command_sep={" ", "　"},           # 命令分隔符
    host="127.0.0.1",
    port=8080,                         # NoneBot 监听端口
    debug=True,
)

# 注册 OneBot v11 适配器
driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11_Adapter)

# 自动加载插件目录
nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════╗
║       🤖 七坛 QQ 机器人              ║
║       基于 NoneBot2 + OneBot v11      ║
║                                      ║
║   监听地址: ws://127.0.0.1:8080      ║
║                                      ║
║   ⚠ 请确保 NapCatQQ 已启动并配置    ║
║     反向WS地址为 ws://127.0.0.1:8080 ║
╚══════════════════════════════════════╝
    """)
    nonebot.run()
