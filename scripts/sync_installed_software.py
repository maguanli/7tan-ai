"""扫描系统已安装软件并同步到数据库"""
import sys
sys.path.insert(0, 'src')
from database.db import get_session, InstalledSoftware, upsert_installed_software
from datetime import datetime

def main():
    # 定义所有要录入的软件（扫描结果）
    software_list = [
        # ===== 编程语言与环境 =====
        {"category": "编程语言与环境", "icon": "🐍", "name": "Python", "version": "3.12.5",
         "install_path": "C:\\Program Files\\Python312", "executable": "C:\\Program Files\\Python312\\python.exe",
         "is_in_path": 1, "sort_order": 1, "notes": "主编程语言，venv 在 .venv"},
        
        {"category": "编程语言与环境", "icon": "📦", "name": "pip", "version": "24.2",
         "install_path": "C:\\Program Files\\Python312\\Lib\\site-packages\\pip",
         "executable": "C:\\Program Files\\Python312\\Scripts\\pip.exe",
         "is_in_path": 1, "sort_order": 2, "notes": "Python 包管理器"},
        
        # ===== 版本控制 =====
        {"category": "版本控制", "icon": "🔀", "name": "Git", "version": "2.54.0.windows.1",
         "install_path": "C:\\Program Files\\Git", "executable": "C:\\Program Files\\Git\\cmd\\git.exe",
         "is_in_path": 1, "sort_order": 10, "notes": "版本控制，含 Git Bash"},
        
        # ===== 视频/音频处理 =====
        {"category": "音视频处理", "icon": "🎬", "name": "FFmpeg", "version": "8.1.2-essentials_build-www.gyan.dev",
         "install_path": "G:\\AI_Tools\\FFmpeg\\ffmpeg-8.1.2-essentials_build",
         "executable": "G:\\AI_Tools\\FFmpeg\\ffmpeg-8.1.2-essentials_build\\bin\\ffmpeg.exe",
         "is_in_path": 0, "sort_order": 20, "notes": "视频编解码核心工具，需用完整路径调用"},
        
        {"category": "音视频处理", "icon": "🎞", "name": "edge-tts", "version": "7.2.8",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\edge_tts",
         "executable": ".venv\\Scripts\\edge-tts.exe",
         "is_in_path": 0, "sort_order": 21, "notes": "微软Edge文字转语音，Python包"},
        
        {"category": "音视频处理", "icon": "🎥", "name": "moviepy", "version": "2.2.1",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\moviepy",
         "executable": "",
         "is_in_path": 0, "sort_order": 22, "notes": "Python视频编辑库，合成+转场+字幕"},
        
        # ===== AI 引擎 =====
        {"category": "AI引擎与模型", "icon": "🤖", "name": "PyTorch", "version": "2.5.1+cpu",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\torch",
         "executable": "",
         "is_in_path": 0, "sort_order": 30, "notes": "深度学习框架，CPU版本"},
        
        {"category": "AI引擎与模型", "icon": "🎨", "name": "Stable Diffusion WebUI", "version": "1.5+",
         "install_path": "G:\\AI_Video\\stable-diffusion-webui",
         "executable": "G:\\AI_Video\\stable-diffusion-webui\\webui.bat",
         "is_in_path": 0, "sort_order": 31, "notes": "AI图像生成，模型: v1-5-pruned-emaonly.safetensors (4GB)"},
        
        {"category": "AI引擎与模型", "icon": "🧩", "name": "ComfyUI", "version": "",
         "install_path": "G:\\AI_Tools\\ComfyUI",
         "executable": "G:\\AI_Tools\\ComfyUI\\run_nvidia_gpu.bat",
         "is_in_path": 0, "sort_order": 32, "notes": "AI图像工作流引擎，节点式"},
        
        # ===== Python 核心库 =====
        {"category": "Python核心库", "icon": "📷", "name": "Pillow", "version": "11.3.0",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\PIL",
         "executable": "",
         "is_in_path": 0, "sort_order": 40, "notes": "图像处理库，截图压缩"},
        
        {"category": "Python核心库", "icon": "🔢", "name": "NumPy", "version": "2.5.1",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\numpy",
         "executable": "",
         "is_in_path": 0, "sort_order": 41, "notes": "科学计算基础库"},
        
        {"category": "Python核心库", "icon": "👁", "name": "OpenCV", "version": "4.13.0.92",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\cv2",
         "executable": "",
         "is_in_path": 0, "sort_order": 42, "notes": "计算机视觉，视频帧处理"},
        
        {"category": "Python核心库", "icon": "🌐", "name": "Gradio", "version": "6.20.0",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\gradio",
         "executable": "",
         "is_in_path": 0, "sort_order": 43, "notes": "AI模型Web界面框架"},
        
        {"category": "Python核心库", "icon": "🍜", "name": "BeautifulSoup4", "version": "4.15.0",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\bs4",
         "executable": "",
         "is_in_path": 0, "sort_order": 44, "notes": "HTML解析，爬虫用"},
        
        {"category": "Python核心库", "icon": "🗄", "name": "SQLAlchemy", "version": "2.0.51",
         "install_path": "D:\\7tan\\7tanAI\\.venv\\Lib\\site-packages\\sqlalchemy",
         "executable": "",
         "is_in_path": 0, "sort_order": 45, "notes": "数据库ORM框架"},
        
        # ===== 开发工具/IDE =====
        {"category": "开发工具与IDE", "icon": "💻", "name": "VS Code", "version": "",
         "install_path": "C:\\Users\\Administrator\\AppData\\Local\\Programs\\Microsoft VS Code",
         "executable": "C:\\Users\\Administrator\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
         "is_in_path": 1, "sort_order": 50, "notes": "主力编辑器，code 命令可用"},
        
        # ===== 未安装但需要的工具（标记为未工作）=====
        {"category": "移动端开发(未安装)", "icon": "☕", "name": "Java JDK", "version": "",
         "install_path": "", "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 60, "notes": "❌ 未安装 — Android编译必需"},
        
        {"category": "移动端开发(未安装)", "icon": "📱", "name": "Android SDK", "version": "",
         "install_path": "", "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 61, "notes": "❌ 未安装 — ANDROID_HOME 未设置"},
        
        {"category": "移动端开发(未安装)", "icon": "🏗", "name": "Gradle", "version": "",
         "install_path": "C:\\Users\\Administrator\\.gradle (仅缓存)",
         "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 62, "notes": "❌ 未安装 — 仅有 .gradle 缓存目录"},
        
        {"category": "移动端开发(未安装)", "icon": "🔌", "name": "ADB", "version": "",
         "install_path": "", "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 63, "notes": "❌ 未安装 — Android Debug Bridge，APK安装调试"},
        
        {"category": "容器与编排(未安装)", "icon": "🐳", "name": "Docker", "version": "",
         "install_path": "", "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 70, "notes": "❌ 未安装 — 容器运行时"},
        
        {"category": "容器与编排(未安装)", "icon": "☸", "name": "kubectl", "version": "",
         "install_path": "", "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 71, "notes": "❌ 未安装 — Kubernetes 命令行"},
        
        {"category": "前端开发(未安装)", "icon": "🟢", "name": "Node.js", "version": "",
         "install_path": "", "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 80, "notes": "❌ 未安装 — JavaScript 运行时"},
        
        {"category": "前端开发(未安装)", "icon": "📦", "name": "npm", "version": "",
         "install_path": "", "executable": "",
         "is_in_path": 0, "is_working": 0, "sort_order": 81, "notes": "❌ 未安装 — Node.js 包管理器"},
    ]
    
    # 录入数据库
    updated = 0
    added = 0
    for sw_data in software_list:
        name = sw_data["name"]
        is_working = sw_data.get("is_working", 1)
        try:
            result = upsert_installed_software(
                name=name,
                category=sw_data["category"],
                version=sw_data["version"],
                install_path=sw_data["install_path"],
                executable=sw_data["executable"],
                is_in_path=sw_data["is_in_path"],
                is_working=is_working,
                icon=sw_data["icon"],
                sort_order=sw_data["sort_order"],
                notes=sw_data["notes"],
            )
            if result:
                added += 1
        except Exception as e:
            print(f"ERROR: {name} -> {e}")
    
    # 最终统计
    session = get_session()
    total = session.query(InstalledSoftware).count()
    working = session.query(InstalledSoftware).filter(InstalledSoftware.is_working == 1).count()
    missing = total - working
    session.close()
    
    print(f"=" * 50)
    print(f"同步完成！")
    print(f"  总计: {total} 条")
    print(f"  已安装可用: {working} 条")
    print(f"  未安装: {missing} 条")
    print(f"=" * 50)

if __name__ == "__main__":
    main()
