# gzh_publish 平台变体说明

本插件为 Windows 专属（公众号发布依赖 Windows 版微信 PC 客户端，桌面自动化操作）。
macOS / Linux（含鸿蒙PC Linux生态）用户首次打开 7Tan WEB 版时，点击【确认适配】后，
适配器会自动把对应平台的变体复制到插件目录并安装依赖。

## 目录结构

```
gzh_publish/
├── tools.py                    # Windows 版（原版，仅 Windows 使用）
└── variants/
    ├── darwin/                 # macOS 变体
    │   ├── tools.py            #   友好提示版（返回"请用 Windows 版或网页后台"）
    │   ├── requirements-darwin.txt
    │   └── README.md
    ├── linux/                  # Linux（含鸿蒙PC Linux生态）变体
    │   ├── tools.py
    │   ├── requirements-linux.txt
    │   └── README.md
    └── backup/                 # 复制变体时自动备份被覆盖的原文件（适配器生成）
```

## 变体说明

macOS / Linux 没有微信 PC 客户端，无法进行桌面自动化发布。
变体 tools.py 与 Windows 版保持**同名工具函数**（gzh_xxx），全部返回友好指引：
- 用 Windows 版 7Tan 完成公众号发布
- 或登录网页版公众号后台（mp.weixin.qq.com）手动发布

未来若支持公众号官方 API 发布（appid/secret），直接升级变体 tools.py 即可，
无需改动插件框架与上层调用。
