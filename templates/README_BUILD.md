# 7Tan 完整版 — 源码构建指南

本目录（`7tan-src/`）包含 7Tan 的**完整源码与构建工具链**。
使用本目录可以自行构建出 `7tan-editor.exe`（构建产物仅供个人使用）。

> ⚠️ **授权说明**：本软件版权归开发者所有。源码与构建产物**仅限个人学习/使用**，
> **禁止**将构建产物打包再分发、转售或用于任何商业用途（含制作发布包销售）。

## 目录结构

```
7tan-src/
├── main.py                      # 程序入口
├── build.spec                   # PyInstaller 构建配置
├── build.bat                    # 构建 exe（推荐入口）
├── setup.bat                    # 一键环境准备（建 venv + 装依赖）
├── requirements.txt             # Python 依赖清单
├── src/                         # 全部源码
├── config/                      # 配置文件（密钥用环境变量占位）
├── data/
│   ├── plugins/                 # 插件系统（44 个插件 + 白名单）
│   └── logo/                    # 图标素材
└── tools/
    ├── gen_plugin_hashes.py     # 插件白名单生成（构建链必需）
    └── security_src/            # 安全模块源码（.pyd 的 Python 源）
```

## 环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | Windows 10/11 64 位 |
| Python | 3.12（3.11+ 亦可） [下载](https://www.python.org/downloads/) |
| 磁盘 | 至少 5GB 可用空间（构建产物较大） |

## 构建 exe（推荐）

```bat
:: 1. 首次使用：准备环境（创建 .venv 并安装全部依赖，约 2-5 分钟）
setup.bat

:: 2. 构建 exe（约 10-15 分钟，输出到 dist\7tan-editor\）
build.bat
```

构建完成后，`dist\7tan-editor\7tan-editor.exe` 即为可运行程序
（需连同 `dist\7tan-editor\_internal` 目录一起使用）。

## 手动构建（进阶）

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: 构建 exe（输出到 dist\7tan-editor\）
.venv\Scripts\python.exe -m PyInstaller build.spec --clean -y
```

## 配置说明

- 密钥均使用环境变量占位：`config/config.yaml` 中的
  `${DEEPSEEK_API_KEY}`、`${OSS_ACCESS_KEY}` 等。
  运行前请设置对应环境变量，或直接编辑 config.yaml 填入实际值。
- 首次运行会自动生成本地加密密钥（`.encryption_key`），请勿删除。

## 安全模块说明

`src/security/` 下的 `.pyd` 为编译好的安全模块（RSA 验签、授权校验、文件完整性等）。
如需从源码重新编译，参考 `tools/security_src/` 中的 Python 源文件与根目录 `setup_cython.py`。

## 商业模式

- 软件本体免费分发
- 付费插件（如「爆款写作」50 元/台，绑定设备永久授权）在软件内「设置 → 插件市场」购买激活
- **本包不含发布打包脚本**，构建产物仅限个人使用，禁止再分发/转售

## 常见问题

**Q: 构建失败，提示模块找不到？**
A: 确认已运行 `setup.bat` 且无报错；或手动执行
`.venv\Scripts\python.exe -m pip install -r requirements.txt`。

**Q: 杀毒软件拦截构建？**
A: PyInstaller 构建行为正常，将项目目录加入杀软白名单即可。

**Q: 构建出的 exe 双击无反应？**
A: 在命令行运行 `dist\7tan-editor\7tan-editor.exe` 查看报错输出。
