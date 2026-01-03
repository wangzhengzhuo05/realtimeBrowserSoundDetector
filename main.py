# -*- coding: utf-8 -*-
"""
================================================================================
课堂监听报警系统 - Classroom Audio Monitor & Alert System
================================================================================

功能说明:
    通过浏览器插件捕获网课直播音频，使用 ASR 语音识别引擎将语音转为文本，
    当检测到老师说出特定"关键词"时，触发报警通知。

    v2.1 新增 Web 控制面板，可在浏览器中设置 API Key、关键词等参数。

依赖安装:
    pip install websockets numpy dashscope colorama aiohttp

    如果使用本地 FunASR 模式，还需安装:
    pip install funasr torch torchaudio modelscope

使用方法:
    1. 运行: python main.py
    2. 打开浏览器访问 http://localhost:8080 配置系统参数
    3. 在 Chrome 浏览器中加载 browser_extension 文件夹作为扩展
    4. 打开网课页面，点击插件图标开始捕获音频

================================================================================
"""

from colorama import init, Fore, Style

from config_manager import config
from monitor_web import ClassroomMonitor

# 初始化 colorama (Windows 终端颜色支持)
init(autoreset=True)


def main():
    """主函数"""
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║          课堂监听报警系统 v2.1                                ║
║          Classroom Audio Monitor & Alert System              ║
║                                                              ║
║          🌐 浏览器插件模式 + Web 控制面板                     ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")
    
    # 显示当前配置
    mode_text = "阿里云 DashScope API" if config.use_cloud_api else "本地 FunASR"
    print(f"{Fore.CYAN}当前 ASR 模式: {mode_text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}音频 WebSocket: ws://{config.ws_host}:{config.ws_port}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Web 控制面板: http://{config.web_host}:{config.web_port}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}监控关键词: {', '.join(config.keywords)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}报警冷却时间: {config.cooldown} 秒{Style.RESET_ALL}")
    
    # 检查 API Key（如果使用云端模式）
    if config.use_cloud_api and not config.api_key:
        print(f"\n{Fore.YELLOW}[提示] 请先配置 DashScope API Key！{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}访问 http://{config.web_host}:{config.web_port} 进行配置{Style.RESET_ALL}")
    
    # 显示浏览器插件安装说明
    print(f"\n{Fore.YELLOW}{'='*60}")
    print("使用说明:")
    print(f"{'='*60}{Style.RESET_ALL}")
    print(f"""
1. 访问 {Fore.GREEN}http://{config.web_host}:{config.web_port}{Style.RESET_ALL} 配置系统参数
2. 打开 Chrome 浏览器，访问 chrome://extensions/
3. 开启 "开发者模式"，加载 browser_extension 文件夹
4. 打开网课页面，点击插件图标开始捕获音频
""")
    
    # 创建并启动监听器
    monitor = ClassroomMonitor()
    monitor.start()


if __name__ == "__main__":
    main()
