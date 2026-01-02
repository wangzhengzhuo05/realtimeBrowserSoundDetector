# -*- coding: utf-8 -*-
"""
课堂监听主控制器
协调 WebSocket 服务器、ASR 识别和关键词报警
"""

from colorama import Fore, Style

from config import (
    USE_CLOUD_API, 
    DASHSCOPE_API_KEY,
    WS_HOST,
    WS_PORT,
    ALERT_KEYWORDS, 
    ALERT_COOLDOWN,
    CUSTOM_ALERT_SOUND
)
from audio import AudioWebSocketServer
from asr import DashScopeASR, FunASREngine
from alert import KeywordAlert


class ClassroomMonitor:
    """
    课堂监听主控制器
    协调 WebSocket 服务器、ASR 识别和关键词报警
    """
    
    def __init__(self, use_cloud_api: bool = True):
        self.use_cloud_api = use_cloud_api
        
        # 初始化 WebSocket 服务器
        self.ws_server = AudioWebSocketServer(WS_HOST, WS_PORT)
        
        # 初始化关键词报警（支持自定义报警音频）
        self.keyword_alert = KeywordAlert(ALERT_KEYWORDS, ALERT_COOLDOWN, CUSTOM_ALERT_SOUND)
        
        # 根据配置选择 ASR 引擎
        if use_cloud_api:
            print(f"{Fore.CYAN}[信息] 使用阿里云 DashScope API 模式{Style.RESET_ALL}")
            self.asr_engine = DashScopeASR(DASHSCOPE_API_KEY)
        else:
            print(f"{Fore.CYAN}[信息] 使用本地 FunASR 模式{Style.RESET_ALL}")
            self.asr_engine = FunASREngine()
        
        self.is_running = False
        self.text_buffer = ""  # 用于累积识别文本
        
    def _on_text_result(self, text: str):
        """ASR 识别结果回调"""
        if text:
            # 显示识别结果
            print(f"{Fore.WHITE}[识别] {text}{Style.RESET_ALL}")
            
            # 累积文本并检查关键词
            self.text_buffer += text
            
            # 检查关键词
            self.keyword_alert.check_and_alert(self.text_buffer)
            
            # 保持缓冲区在合理长度（避免内存无限增长）
            if len(self.text_buffer) > 500:
                self.text_buffer = self.text_buffer[-200:]
    
    def _on_audio_data(self, audio_data: bytes):
        """音频数据回调（来自 WebSocket）"""
        if self.is_running:
            self.asr_engine.feed_audio(audio_data)
    
    def start(self):
        """启动监听"""
        print(f"\n{Fore.GREEN}{'='*60}")
        print("课堂监听报警系统启动中...")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        
        try:
            # 设置 ASR 回调
            self.asr_engine.set_result_callback(self._on_text_result)
            
            # 启动 ASR 引擎
            self.asr_engine.start()
            
            # 设置 WebSocket 音频回调
            self.ws_server.set_audio_callback(self._on_audio_data)
            
            self.is_running = True
            
            print(f"\n{Fore.GREEN}系统已就绪，等待浏览器插件连接...{Style.RESET_ALL}")
            print(f"{Fore.CYAN}监控关键词: {', '.join(ALERT_KEYWORDS)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}按 Ctrl+C 停止服务{Style.RESET_ALL}\n")
            
            # 启动 WebSocket 服务器（会阻塞）
            self.ws_server.start()
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}收到停止信号...{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[错误] 运行时错误: {e}{Style.RESET_ALL}")
        finally:
            self.stop()
    
    def stop(self):
        """停止监听"""
        self.is_running = False
        
        print(f"\n{Fore.CYAN}正在停止系统...{Style.RESET_ALL}")
        
        # 停止 WebSocket 服务器
        try:
            self.ws_server.stop()
        except:
            pass
        
        # 停止 ASR 引擎
        try:
            self.asr_engine.stop()
        except:
            pass
        
        print(f"{Fore.GREEN}系统已安全停止{Style.RESET_ALL}")
