# -*- coding: utf-8 -*-
"""
================================================================================
课堂监听报警系统 - Classroom Audio Monitor & Alert System
================================================================================

功能说明:
    通过浏览器插件捕获网课直播音频，使用 ASR 语音识别引擎将语音转为文本，
    当检测到老师说出特定"关键词"时，触发报警通知。

依赖安装:
    pip install websockets numpy dashscope colorama

    如果使用本地 FunASR 模式，还需安装:
    pip install funasr torch torchaudio modelscope

使用方法:
    1. 配置 config.py 中的 API Key 和其他参数
    2. 运行: python main.py
    3. 在 Chrome 浏览器中加载 browser_extension 文件夹作为扩展
    4. 打开网课页面，点击插件图标开始捕获音频

================================================================================
"""

from colorama import init, Fore, Style

from config import USE_CLOUD_API, DASHSCOPE_API_KEY, ALERT_KEYWORDS, ALERT_COOLDOWN, WS_HOST, WS_PORT
from monitor import ClassroomMonitor

# 初始化 colorama (Windows 终端颜色支持)
init(autoreset=True)


def main():
    """主函数"""
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║          课堂监听报警系统 v2.0                                ║
║          Classroom Audio Monitor & Alert System              ║
║                                                              ║
║          🌐 浏览器插件模式                                    ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")
    
    # 显示当前配置
    mode_text = "阿里云 DashScope API" if USE_CLOUD_API else "本地 FunASR"
    print(f"{Fore.CYAN}当前 ASR 模式: {mode_text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}WebSocket 地址: ws://{WS_HOST}:{WS_PORT}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}监控关键词: {', '.join(ALERT_KEYWORDS)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}报警冷却时间: {ALERT_COOLDOWN} 秒{Style.RESET_ALL}")
    
    # 检查 API Key（如果使用云端模式）
    if USE_CLOUD_API and DASHSCOPE_API_KEY == "your-dashscope-api-key-here":
        print(f"\n{Fore.RED}[错误] 请先配置 DASHSCOPE_API_KEY！{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}在 config.py 中找到 DASHSCOPE_API_KEY 变量，填入您的 API Key{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}获取方式请参考 config.py 顶部的说明{Style.RESET_ALL}")
        return
    
    # 显示浏览器插件安装说明
    print(f"\n{Fore.YELLOW}{'='*60}")
    print("浏览器插件安装说明:")
    print(f"{'='*60}{Style.RESET_ALL}")
    print(f"""
1. 打开 Chrome 浏览器，访问 chrome://extensions/
2. 开启右上角的 "开发者模式"
3. 点击 "加载已解压的扩展程序"
4. 选择项目中的 browser_extension 文件夹
5. 插件安装完成后，打开网课页面
6. 点击插件图标，点击 "开始捕获音频"
""")
    
    # 创建并启动监听器
    monitor = ClassroomMonitor(USE_CLOUD_API)
    monitor.start()


if __name__ == "__main__":
    main()
