# 🎬 7Tan Video Editor（代号「青锋」）— 架构设计文档 v1.6

> 最后更新：2026-07-19
> v1.6 更新：新增 Transition、统一 Project/ProjectData、cover_path→cover_data、封面版本历史、RecordingConfig+mic_device_id、导出支持封面/音频、VLC/MPV双引擎说明、AI撤销指令、QPainter入选型表
> v1.5 更新：补充数据模型、封面模块交互说明、AI导出指令、filter_complex说明、录屏刷新机制、修正文件计数
> v1.4 更新：修复 Track/SubtitleClip、补充 AI 封面否定意图闭环、新增 pip 依赖清单、明确 SD 模型路径
> v1.3 更新：新增第九章封面制作详解、修复数据模型、删除重复快捷键、补充导出引擎与项目管理设计

---

## 一、产品定位

```
┌─────────────────────────────────────────────────────────────┐
│  7Tan Video Editor — 嵌入 7Tan AI 桌面端的轻量级剪辑器       │
│                                                               │
│  定位：剪映的 20% 功能 → 覆盖 80% 日常需求                    │
│  核心亮点：                                                  │
│    1. AI 自然语言驱动剪辑 — 在对话框说人话，AI 帮你剪        │
│    2. 内置电脑录屏 — 免装第三方软件，录完自动导入素材库      │
│    3. AI 封面制作 — 一键生成视频封面，文字/模板/AI生图     │
│  优势：本地运行、AI 驱动、与 7Tan 生态无缝集成               │
└─────────────────────────────────────────────────────────────┘
```


## 二、三大亮点功能

### 🌟 亮点一：AI 自然语言剪辑

用户只需在 7Tan 对话框中说人话，AI 自动操作剪辑器：

```
用户：把第三段删掉，然后把第一段和第二段交换位置
  → AI 解析意图 → 调用剪辑器 API → 完成操作 → 回复"已搞定"

用户：给第5秒到第12秒加一个0.5倍慢动作
  → AI 设置片段变速 → 回复结果

用户：从这段视频里截取第30秒到第90秒，导出为 720p
  → AI 精确定位切割 → 设置导出参数 → 导出

用户：帮我做一个15秒预告片，快节奏，配上刚生成的配音
  → AI 自动选取素材 → 切割 → 变速 → 配音 → 合成
```

**AI 剪辑引擎设计**：

| 层级 | 职责 |
|------|------|
| **意图识别** | ChatPage 中识别剪辑相关意图，区分普通对话和剪辑指令 |
| **指令解析** | 自然语言 → 结构化剪辑操作（JSON） |
| **操作执行** | 调用 VideoEditor 暴露的 API |
| **结果反馈** | 返回执行结果，必要时附带预览截图 |

### 🌟 亮点二：AI 封面制作

一键生成视频封面图：

| 功能 | 说明 |
|------|------|
| 帧截图封面 | 自动选取视频中的关键帧作为封面候选 |
| 文字叠加 | AI 自动生成标题文字，可调字体/颜色/位置 |
| 模板封面 | 预设封面模板（游戏解说、Vlog、教程等风格） |
| AI 生成封面 | 对接 SD 模型，根据视频内容生成封面图 |

### 🌟 亮点三：电脑录屏（内置）

免装任何第三方录屏软件，直接在 7Tan 中录制屏幕：

| 特性 | 说明 |
|------|------|
| 三种模式 | 全屏录制 / 自定义区域 / 指定窗口 |
| 系统音频 | WASAPI loopback，不装虚拟声卡直接捕获系统声音 |
| 麦克风混音 | 系统声音 + 麦克风同时录制（游戏解说必备） |
| 悬浮控制条 | 录制中显示计时器 + 暂停/停止按钮 |
| 快捷键 | Ctrl+Shift+R 开始/停止，Ctrl+Shift+P 暂停/继续（详见 8.6） |
| 自动导入 | 录完通过回调通知 media_bin.refresh() 刷新素材面板 |


---

## 三、核心功能清单

| 模块 | 优先级 | 说明 |
|------|:--:|------|
| 📁 **素材管理** | P0 | 导入视频/图片/音频，缩略图预览，拖拽排序 |
| 🎬 **视频播放器** | P0 | 基于 VLC 引擎，播放/暂停/逐帧/倍速/截图 |
| ✂️ **时间轴** | P0 | 多轨道（视频1轨 + 音频2轨 + 字幕1轨） |
| 🔪 **切割** | P0 | 分割片段、删除、拖拽调整顺序 |
| 🤖 **AI 剪辑引擎** | P0 | 自然语言 → 剪辑操作（核心亮点！） |
| 🎥 **电脑录屏** | P0 | mss + FFmpeg + WASAPI，全屏/区域/窗口 |
| 🎙️ **AI 配音** | P1 | 接入已有 Edge TTS，文字→语音直接拖入时间轴 |
| 📝 **AI 字幕** | P1 | 语音识别 → 自动生成字幕轨道 |
| 🖼️ **封面制作** | P1 | 帧截图 + 文字 + 模板 + AI 生成 |
| 🌈 **滤镜/调色** | P2 | 亮度/对比度/饱和度 + 预设滤镜 |
| 🔄 **转场** | P2 | 淡入淡出/推拉/擦除等 |
| 📤 **导出** | P1 | H.264/H.265 MP4，可调分辨率/码率 |

---

## 四、技术选型

| 组件 | 方案 | 原因 |
|------|------|------|
| **UI 框架** | PyQt6 | 7Tan 已有，不引入新依赖 |
| **播放器内核** | VLC (python-vlc) | 成熟稳定，逐帧/倍速/截图全支持 |
| **时间轴渲染** | QGraphicsScene | 高性能 2D 场景，适合自定义时间轴 |
| **视频合成** | FFmpeg CLI | 已有，导出用 filter_complex（多轨叠加），简单拼接可用 concat demuxer 加速 |
| **缩略图生成** | FFmpeg thumbnail | 已有，素材导入时自动生成 |
| **屏幕捕获** | mss 库 | 跨平台、高性能屏幕截图 |
| **系统音频** | WASAPI (Windows) | 无需虚拟声卡，loopback 直录系统声音 |
| **麦克风** | PyAudio | 跨平台音频采集 |
| **AI 能力** | 复用 ai_video 插件 | TTS/字幕/增强，不重复造轮子 |
| **AI 剪辑意图** | 盘古自身推理 | 利用现有 AI 对话能力，无需额外模型 |
| **封面渲染** | PyQt6 QPainter | 封面编辑器逐层绘制，PyQt6 内置无需额外安装 |

### 4-A、pip 依赖清单

以下为视频剪辑器所需的新增依赖（不含 7Tan 已有依赖如 PyQt6/FFmpeg）。

```bash
# 播放器内核
pip install python-vlc          # VLC 播放器绑定（需先安装 VLC 桌面版）

# 录屏
pip install mss                 # 屏幕截图捕获
pip install pyaudio             # 麦克风音频采集

# 选装（VLC 备选 / 高级场景）
pip install python-mpv          # mpv 播放器绑定。VLC 为主力引擎，mpv 为备选。
                                # VLC 生态成熟、兼容性好；mpv 在低延迟和 HDR 方面更优。
                                # 默认使用 VLC，用户可在设置中切换引擎。
```

> **注意**：系统音频捕获（WASAPI）由 FFmpeg 原生支持，无需额外 Python 包。FFmpeg 已在 `G:\AI_Video\ffmpeg` 就绪。VLC 桌面版需手动安装，python-vlc 会自动检测 VLC 安装位置。


---

## 五、文件结构

```
D:\7tan\7tanAI\src\ui\video_editor\
├── __init__.py               # 模块导出
├── editor_window.py          # 剪辑器主窗口（VideoEditorPage）
├── media_bin.py              # 素材管理面板
├── player.py                 # 视频播放器（VLC 内核）
├── timeline.py               # 时间轴组件
├── timeline_items.py         # 时间轴视图层（QGraphicsScene item）
├── cut_tool.py               # 切割工具
├── export_dialog.py          # 导出设置对话框
├── exporter.py               # 导出执行引擎（FFmpeg + 编码参数）
├── project_manager.py        # 项目保存/加载（.7tanproj JSON）
├── ai_tools_panel.py         # AI 配音/字幕面板
├── cover_editor.py           # 封面编辑器（手动模式画布 + QPainter 渲染）
├── cover_ai_engine.py        # 封面 AI 引擎（对话式生成 + SD 模型调用）
├── ai_clip_engine.py         # AI 剪辑引擎（自然语言→操作）
├── commands.py               # 命令模式（ClipCommand / UndoManager）
├── editor_api.py             # 剪辑器 API（供 AI 调用）
├── screen_recorder.py        # 录屏核心（mss + FFmpeg + PyAudio）
├── recorder_overlay.py       # 悬浮控制条（录制中显示）
├── recorder_settings.py      # 录屏设置面板
├── styles.py                 # 样式常量
└── utils.py                  # 工具函数
```
（共 21 个模块）

### 五-A、导出引擎设计（exporter.py）

> 负责将时间轴上的所有片段合成为最终文件。

| 组件 | 说明 |
|------|------|
| **输入** | 项目对象（含所有 Track/Clip），输出路径，编码参数 |
| **核心** | 构建 FFmpeg filter_complex 图（视频缩放+音频混音+字幕烧录）。简单拼接可用 concat demuxer 加速，多轨叠加必须用 filter_complex |
| **进度** | 解析 FFmpeg stderr 获取编码进度，通过信号更新 UI 进度条 |
| **视频格式** | MP4(H.264/H.265)、MOV、WebM(VP9)、GIF |
| **封面导出** | 从 cover_data 渲染 → PNG/JPG（可调分辨率、质量） |
| **音频导出** | 仅音频轨 → MP3(320kbps) / WAV（播客/配音素材） |
| **预设** | 快速预设：B站(1080p30)、抖音(720p竖屏)、原画(原始参数) |

```python
class VideoExporter:
    def export(self, project, output_path, resolution, fps,
               codec, bitrate, on_progress) -> bool: ...
    def export_cover(self, cover_data, output_path,
                     format, quality) -> bool: ...
    def export_audio(self, project, output_path,
                     format, bitrate) -> bool: ...
    def estimate_size(self, project, codec) -> str: ...
```

### 五-B、项目管理设计（project_manager.py）

> 项目文件（.7tanproj）是一个 JSON 文件，保存所有剪辑状态。

| 特性 | 说明 |
|------|------|
| **格式** | JSON（可读可调试），含项目元数据 + 轨道 + 片段 + 历史 |
| **引用** | 源文件用绝对路径 + 相对路径双存储，移动文件夹后可自动修复 |
| **缩略图** | 项目文件旁生成 `.7tanproj.thumbnails/` 目录存放片段缩略图 |
| **自动保存** | 每 60 秒自动保存，崩溃后可恢复 |
| **最近项目** | 维护最近 10 个项目列表，启动时可快速打开 |

```python
class ProjectManager:
    def new_project(self, name, resolution, fps) -> Project: ...
    def save(self, project, path=None) -> bool: ...
    def load(self, path) -> Project: ...
    def auto_save(self, project): ...
    def get_recent_projects(self) -> list[str]: ...
    def recover_autosave(self) -> Project | None: ...
```


---

## 六、窗口布局

```
+------------------+---------------------------+
|                  |                           |
|   素材面板        |     🎬 预览窗口            |
|  (MediaBin)      |    (Player)               |
|                  |                           |
|   📁 视频        |    1920 x 1080            |
|   🖼️ 图片       |                           |
|   🎵 音频        |    ▶ ⏸ ⏪ ⏩ 控制栏      |
|   🎥 录屏素材    |                           |
|                  |                           |
+------------------+---------------------------+
|                                              |
|          ⏱️ 时间轴 (Timeline)                |
|  +--------------------------------------+   |
|  | 🎬 视频轨                            |   |
|  | 🎵 音频轨 1                          |   |
|  | 🎵 音频轨 2                          |   |
|  | 💬 字幕轨                            |   |
|  +--------------------------------------+   |
|                                              |
+----------------------------------------------+
| 🎥录屏 | 🎙️AI配音 | 📝AI字幕 | 🖼️封面 | 📤导出 |
+----------------------------------------------+
```

---

## 七、AI 剪辑引擎详解

### 7.1 架构

```
用户自然语言
      │
      ▼
+-----------------+
|  意图识别层      |  ← ChatPage 判断是否为剪辑指令
|  (Intent Parser) |
+--------+--------+
         │ 是剪辑指令
         ▼
+-----------------+
|  指令解析层      |  ← 自然语言 → 结构化操作
|  (NL → JSON)    |
+--------+--------+
         │
         ▼
+-----------------+
|  操作执行层      |  ← 调用 editor_api.py
|  (API Call)     |
+--------+--------+
         │
         ▼
+-----------------+
|  结果反馈        |  ← 回复用户 + 可选预览截图
|  (Response)     |
+-----------------+
```

### 7.2 支持的自然语言指令示例

| 用户说 | AI 解析为 |
|--------|----------|
| "导入 G 盘那个游戏录屏" | {"action":"import","path":"G:/.../xxx.mp4"} |
| "把第2段删掉" | {"action":"delete_clip","clip_index":2} |
| "第1段和第3段换位置" | {"action":"swap_clips","index_a":1,"index_b":3} |
| "从第30秒切开" | {"action":"split","time":30} |
| "把第2段加速2倍" | {"action":"set_speed","clip_index":2,"speed":2.0} |
| "帮我做一个封面" | {"action":"make_cover","title":"..."} |
| "开始录屏，只录这个窗口" | {"action":"start_recording","mode":"window"} |
| "导出为1080p 60帧" | {"action":"export","resolution":"1920x1080","fps":60} |
| "停止录屏" | {"action":"stop_recording"} |
| "撤销刚才的操作" | {"action":"undo"} |
| "回到上一步" | {"action":"undo"} |

### 7.3 安全边界

- AI 只能操作当前打开的项目
- 删除操作需用户确认
- 不会修改原始文件（非破坏性编辑）
- 导出前提示覆盖确认
- 录屏前检查磁盘空间（>1GB）

### 7.4 撤销/重做（Undo/Redo）

采用**命令模式（Command Pattern）**：

```
每个操作封装为 Command 对象 → 执行后压入历史栈
Undo → 从历史栈弹出 → command.undo()
Redo → 从重做栈弹出 → command.redo()
```

| 特性 | 说明 |
|------|------|
| 历史深度 | 默认保留最近 50 步操作 |
| 快捷键 | Ctrl+Z 撤销 / Ctrl+Y 重做 |
| 粒度 | 切割、删除、移动、变速均为一原子操作 |
| 持久化 | 历史栈随项目文件一同保存/加载 |
| 合并 | 连续同类型微调合并为一步 |


---

## 八、录屏模块详解

### 8.1 技术架构

```
屏幕 ──→ mss (30fps截图) ──┐
                              │
系统音频 ──→ WASAPI loopback ──→ FFmpeg 管道 ──→ MP4
                              │
麦克风 ──→ PyAudio ──→ [增益 x0.8] ──┘
```

### 8.2 三种录制模式

| 模式 | 实现方式 | 适用场景 |
|------|---------|---------|
| **全屏** | mss 捕获指定显示器（多屏支持） | 游戏录制、教程演示 |
| **区域** | 用户拖拽选择矩形区域 | 只录某一部分画面 |
| **窗口** | 用户点击选择目标窗口 | 录特定应用窗口 |

### 8.3 悬浮控制条

录制时屏幕上显示小型浮动窗口：

```
+-----------------------------+
|  🔴 录制中  |  00:12:35   |  ⏸ 暂停  |  ⏹ 停止  |
+-----------------------------+
```

- 半透明设计，不遮挡被录画面
- 可拖拽到屏幕任意位置
- 录制完成自动消失

### 8.4 音频路由

```
系统声音 → WASAPI Loopback → 系统音频流 ──┐
                                          ├→ FFmpeg 混音 → 最终音频轨
麦克风   → PyAudio → [增益 x0.8] → 麦克风流 ──┘
```

- 用户可独立开关「系统声音」和「麦克风」
- 麦克风音量可调
- Windows 无需安装任何虚拟声卡

### 8.5 录屏设置

| 参数 | 默认值 | 可选 |
|------|--------|------|
| 帧率 | 30 fps | 15 / 24 / 30 / 60 |
| 编码器 | H.264 (libx264) | H.265 / VP9（实验性） |
| 质量 | CRF 23 | 18(高) ~ 28(低) |
| 系统音频 | ✅ 开启 | 开/关 |
| 麦克风 | ❌ 关闭 | 开/关 |
| 麦克风音量 | 0.8 | 0.0 ~ 1.0 |
| 麦克风设备 | 系统默认 | 可选列表（USB麦克风/内置等） |
| 保存目录 | 素材库默认目录 | 自定义 |

### 8.6 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Shift+R | 开始/停止录制 |
| Ctrl+Shift+P | 暂停/继续录制 |


---

## 九、封面制作详解

> 封面制作是视频剪辑的最后一步，也是吸引观众点击的关键。
> 青锋提供 **手动制作** 和 **AI 交流制作** 两种模式，可自由切换、混合使用。

### 9.1 双模式设计

```
用户进入封面制作面板
      │
      ├── 🖐️ 手动模式 ──→ 拖拽式编辑器
      │     ├── 画布 (1280x720)
      │     ├── 文字图层（字体/大小/颜色/描边/阴影/对齐）
      │     ├── 图片图层（拖入/裁剪/滤镜/透明度）
      │     ├── 背景层（纯色/渐变色/图片/AI生成）
      │     ├── 图层管理（上下移动/显示隐藏/锁定）
      │     └── 导出 JPG/PNG（可调质量）
      │
      └── 🤖 AI 交流模式 ──→ 对话式生成
            ├── 用户在7Tan对话框说需求
            ├── AI 理解意图 → 选模板 → 生成背景 → 排版 → 渲染
            ├── 不满意？继续说"标题放大，颜色改红色"
            └── 满意后一键导出

💡 最佳工作流：AI 生成初稿（30秒） → 手动微调（随心所欲） → 导出
```

### 9.2 模块交互：cover_editor <-> cover_ai_engine

> AI 生成的封面最终需要在画布上渲染预览。

```
cover_ai_engine.generate(prompt) → 输出结果字典
     │
     ├── background_file: str     # 背景图路径
     ├── layers: list[dict]       # 图层JSON
     └── template_name: str       # 使用的模板名
     │
     ▼
cover_editor.load_result(result)  # 载入到画布渲染
     │
     ▼
用户在画布上继续手动微调 → 导出
```

- `cover_ai_engine` 不直接渲染，只生成结构化结果
- `cover_editor` 负责所有渲染（QPainter 逐层绘制），AI 和手动共用同一管线
- 用户可在 AI 生成后切换到手动模式继续编辑

### 9.3 手动模式 — 画布编辑器

| 组件 | 说明 |
|------|------|
| **画布** | 1280x720（9:16竖版可切换），可缩放/平移 |
| **文字工具** | 点击画布添加文字，右侧属性面板调节参数 |
| **图片工具** | 从素材库拖入，支持裁剪/缩放/旋转 |
| **图层列表** | 左侧图层面板，拖动排序，每个图层可独立控制 |
| **背景** | 纯色拾色器 / 渐变编辑器 / 图片 / AI生成 |
| **对齐辅助** | 智能参考线 + 吸附对齐 + 居中/分布工具 |
| **模板库** | 预设模板（游戏解说/Vlog/教程/搞笑），一键套用 |

### 9.4 AI 交流模式 — 对话式生成

```
用户：帮我做个赛博朋克风格的封面，标题「AI改变世界」，副标题「2026深度测评」
      │
      ▼
+----------------+
|  意图理解      |  提取：风格=赛博朋克, 标题=AI改变世界, 副标题=2026深度测评
+------+---------+
       ▼
+----------------+
|  背景生成      |  方案A：SD模型生成赛博朋克风格背景
|                |  方案B：从模板库匹配相似风格模板
|                |  方案C：纯色+霓虹光效滤镜模拟
+------+---------+
       ▼
+----------------+
|  排版布局      |  LLM输出：标题(居中, 字体=科技感, 大小=72px, 颜色=#00FFFF)
|                |          副标题(下方, 字体=细黑, 大小=36px, 颜色=#FFFFFF)
|                |          装饰元素(霓虹边框, 扫描线效果)
+------+---------+
       ▼
+----------------+
|  渲染预览      |  在画布上展示 → 用户审阅
+------+---------+
       ▼ (不满意)
+----------------+
|  迭代修改      |  用户："标题放大点，颜色改橙红色"
|                |  AI：调整字号→84px, 颜色→#FF4400, 重新渲染
|                |  用户："副标题去掉，加个游戏手柄图标"
|                |  AI：移除副标题层, 素材库搜索/生成手柄图标, 置于左下角
|                |
|                |  用户："不太好看，换个风格"
|                |  AI：识别否定意图 → 切换模板 → 重新生成（保留标题文字）
|                |  用户："算了，回到上一版"
|                |  AI：从 _history 栈弹出 → 回退到上一个版本
+------+---------+
       ▼ (满意)
   导出封面 ✅
```

### 9.5 AI 封面引擎详解

| 步骤 | 技术实现 | 说明 |
|------|---------|------|
| **意图提取** | 盘古自身推理 | 从用户消息中提取风格、标题、副标题、情绪、色彩偏好 |
| **背景获取** | SD WebUI API / Unsplash / 纯色 | 优先AI生成，失败降级为模板或纯色。SD 服务 http://127.0.0.1:7860，API: /sdapi/v1/txt2img |
| **排版推理** | LLM 输出 JSON | {"layers":[{"type":"text","x":640,"y":360,"font":"科技","size":72,"color":"#00FFFF","content":"AI改变世界"}]} |
| **渲染** | PyQt QPainter | 根据 JSON 在画布上逐层绘制 |
| **反馈闭环** | 迭代修改 | 用户自然语言反馈 → 解析修改项 → 重新渲染 |
| **版本历史** | _history: list[dict] 栈 | 每次生成/修改前自动 push 当前状态，支持「回到上一版」回退。栈深度默认 20 层 |

### 9.6 封面模板

| 模板风格 | 适用场景 | 配色 |
|------|------|------|
| 🎮 游戏解说 | B站/抖音游戏视频 | 霓虹色+粗体字 |
| 📹 Vlog | 日常记录 | 清新自然色 |
| 📚 教程 | 知识分享 | 简洁白+强调色 |
| 😂 搞笑 | 娱乐向 | 亮黄+夸张字体 |
| 🔧 科技 | 数码测评 | 深色+科技蓝 |
| 🎨 自定义 | 用户自由发挥 | 任意 |

### 9.7 封面制作面板布局

```
+----------+-----------------------+--------------+
| 图层列表  |                       |  属性面板     |
|          |      🎨 画布          |              |
| +------+ |                       |  文字属性    |
| |文字1  | |    1280 x 720        |  字体: ___   |
| |图片1  | |                       |  大小: ___   |
| |背景   | |                       |  颜色: ███   |
| +------+ |                       |  描边: ___   |
|          |                       |  阴影: ___   |
| [+图层]  |                       |              |
+----------+-----------------------+--------------+
|  🖐️手动 | 🤖AI生成 | 📁模板 | 📤导出JPG | 📤导出PNG |
+-----------------------------------------------------+
```


---

## 十、面板按钮位置

在 `ChatBrowserSplitPage` 顶部按钮栏中，按钮排列顺序调整为：

```
🌐 浏览器  →  📝 源代码  →  🎬 视频剪辑器  →  📟 控制台
   索引0          索引1           索引2            索引3
```

点击「🎬 视频剪辑器」→ 切换 _browser_stack 到索引 2（视频剪辑器面板）。

---

## 十一、数据模型

```python
class Clip:
    """时间轴上的一个片段"""
    id: str
    source_path: str       # 源文件路径
    type: "video" | "audio" | "image"
    track_index: int       # 所在轨道
    timeline_start: float  # 在时间轴上的起始秒
    source_start: float    # 裁剪起始（源文件秒数）
    source_end: float      # 裁剪结束
    duration: float        # 持续时长
    speed: float           # 播放速度（1.0=正常）
    properties: dict       # 音量/滤镜参数等
    # 注：type="image" 的片段放在视频轨 (track_index=0)，默认持续 5 秒

class SubtitleClip:
    """字幕片段（独立模型，不走 Clip）"""
    id: str
    text: str              # 字幕文本
    start_time: float      # 开始时间（秒）
    end_time: float        # 结束时间（秒）
    track_index: int       # 所在字幕轨道
    font: str              # 字体
    font_size: int         # 字号
    color: str             # 颜色（HEX）
    position: str          # 位置：bottom / top / center
    has_outline: bool      # 是否有描边

class Track:
    """一个轨道。type="video"|"audio"→list[Clip]; type="subtitle"→list[SubtitleClip]"""
    type: "video" | "audio" | "subtitle"
    clips: list[Clip | SubtitleClip]
    muted: bool
    locked: bool

class Project:
    """项目文件（运行时对象）。ProjectData 是其 JSON 序列化形态，二者字段一致。"""
    version: str           # 格式版本号
    name: str
    file_path: str         # .7tanproj 路径（仅运行时，不存入 JSON）
    created_at: str
    modified_at: str
    tracks: list[Track]
    resolution: tuple[int,int]
    fps: int
    duration: float
    cover_data: dict | None     # 封面图层树，None=无封面
    undo_stack: list       # 撤销命令历史
    transitions: list[Transition]  # 转场效果列表（参见 Transition 模型）

class RecordingConfig:
    """录屏配置"""
    mode: "fullscreen" | "region" | "window"
    fps: int               # 默认 30
    codec: str             # 默认 libx264
    quality: int           # CRF 23
    capture_system_audio: bool  # 默认 True
    capture_mic: bool      # 默认 False
    mic_volume: float      # 0.0 ~ 1.0
    mic_device_id: int | None  # PyAudio 设备索引，None=系统默认
    output_dir: str
    region_rect: tuple[int,int,int,int]  # (x, y, w, h)
    window_title: str      # 窗口模式

class ExporterConfig:
    """导出配置（参见五-A）"""
    export_type: str             # video / cover_image / audio_only
    resolution: tuple[int,int]   # 仅 video / cover
    fps: int                     # 仅 video
    codec: str                   # libx264 / libx265 / vp9 / png / jpg / mp3 / wav
    bitrate: str                 # 仅 video / audio
    quality: int                 # 封面图片质量 / 音频比特率等级
    output_format: str           # mp4 / mov / webm / gif / png / jpg / mp3 / wav
    preset: str                  # fast / medium / slow（仅 video）

class ProjectData:
    """项目持久化结构 — .7tanproj JSON 格式，与 Project 字段一一对应。file_path 不存入 JSON。"""
    version: str
    name: str
    resolution: tuple[int,int]
    fps: int
    tracks: list[Track]
    cover_data: dict | None      # 封面图层树，与 Project.cover_data 一致
    undo_stack: list
    duration: float
    created_at: str
    modified_at: str

class CoverTemplate:
    """封面模板（参见 9.6）"""
    name: str                    # 模板名称
    style: str                   # 风格标签：游戏/Vlog/教程/搞笑/科技/自定义
    bg_color: str                # 默认背景色 HEX
    gradient: str | None         # 渐变CSS样式（可选）
    font: str                    # 默认标题字体
    title_position: tuple[int,int]  # 标题(x,y)
    subtitle_position: tuple[int,int] | None
    decor_elements: list[str]    # 装饰元素

class Transition:
    """转场效果 — 两个相邻片段之间的过渡（参见第三章 Phase 6）"""
    id: str
    type: str                    # fade / dissolve / wipe / slide / zoom / none
    duration: float              # 转场持续秒数（默认 0.5）
    prev_clip_id: str            # 前一片段 ID
    next_clip_id: str            # 后一片段 ID
    params: dict                 # 类型特定参数
```

---

## 十二、开发阶段

> 优先级（P0/P1/P2）表示功能重要性，Phase 1~6 表示开发顺序，两者不完全对应。

| 阶段 | 内容 | 说明 |
|------|------|:--:|
| **Phase 1** | 面板壳子 + 按钮接入 + editor_api 骨架 | 让按钮可用 |
| **Phase 2** | 播放器 + 素材导入 + 时间轴显示 | 能看到视频 |
| **Phase 3** | 切割 + 拖拽排列 + 基础导出（仅 H.264 MP4，固定预设） | 能剪视频 |
| **Phase 4** | 录屏模块（mss + WASAPI + 悬浮条） | 能录屏 |
| **Phase 5** | AI 剪辑引擎 + 封面制作 | 🌟 亮点实现 |
| **Phase 6** | 滤镜 + 转场 + 项目保存/加载 | 成熟产品 |

---

## 十三、快捷键一览

### 13.1 播放器快捷键

| 快捷键 | 功能 |
|--------|------|
| Space | 播放 / 暂停 |
| ← / → | 逐帧后退 / 前进 |
| Shift+← / Shift+→ | 跳至上一段 / 下一段 |
| J / K / L | 倒放 / 暂停 / 正放（按多次倍速） |
| Home / End | 跳至项目开头 / 结尾 |
| Ctrl+P | 截图当前帧 → 自动导入素材库 |

### 13.2 时间轴快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+K | 在当前播放位置分割选中片段 |
| Delete | 删除选中片段 |
| Ctrl+Z / Ctrl+Y | 撤销 / 重做 |
| Ctrl+A | 全选片段 |
| Ctrl+C / Ctrl+V | 复制 / 粘贴片段 |
| Ctrl+D | 快速复制选中片段到后方 |
| Ctrl+滚轮 | 横向缩放时间轴 |
| Alt+滚轮 | 纵向缩放轨道高度 |

### 13.3 录屏快捷键

> 参见 [8.6 录屏快捷键](#86-快捷键)，此处不再重复列出。

---

## 十四、与现有系统关系

```
7Tan AI 桌面端
├── ChatPage（对话）
│   └── 识别剪辑指令 → 调用 editor_api
├── ChatBrowserSplitPage
│   └── _browser_stack
│       ├── [0] BrowserPage（浏览器）
│       ├── [1] CodeViewer（源代码）
│       ├── [2] VideoEditorPage（🎬 视频剪辑器） ← 新增
│       └── [3] ConsoleViewer（控制台）
└── ai_video 插件
    └── TTS / 字幕 / ONNX 增强 → 被剪辑器复用
```
