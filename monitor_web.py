# -*- coding: utf-8 -*-
"""
课堂监听主控制器 (Web 增强版)
协调 WebSocket 服务器、ASR 识别、关键词报警和 Web 控制面板
"""

import asyncio
from typing import Optional, List

from colorama import Fore, Style

from config_manager import config
from audio import AudioWebSocketServer
from asr import DashScopeASR, FunASREngine
from alert import KeywordAlert
from web import WebServer


class ClassroomMonitor:
    """
    课堂监听主控制器
    协调 WebSocket 服务器、ASR 识别、关键词报警和 Web 控制面板
    """
    
    def __init__(self):
        # 加载配置
        config.reload()
        
        self.use_cloud_api = config.use_cloud_api
        
        # 初始化 WebSocket 服务器（接收浏览器音频）
        self.ws_server = AudioWebSocketServer(config.ws_host, config.ws_port)
        
        # 初始化关键词报警（支持自定义报警音频）
        self.keyword_alert = KeywordAlert(
            config.keywords, 
            config.cooldown, 
            config.custom_sound
        )
        
        # 根据配置选择 ASR 引擎
        if self.use_cloud_api:
            print(f"{Fore.CYAN}[信息] 使用阿里云 DashScope API 模式{Style.RESET_ALL}")
            self.asr_engine = DashScopeASR(config.api_key)
        else:
            print(f"{Fore.CYAN}[信息] 使用本地 FunASR 模式{Style.RESET_ALL}")
            self.asr_engine = FunASREngine()
        
        # 初始化 Web 控制面板
        self.web_server = WebServer(config.web_host, config.web_port)
        self.web_server.set_restart_callback(self._handle_restart)
        
        self.is_running = False
        self.text_buffer = ""  # 用于累积识别文本
        self._restart_requested = False
        self._loop = None  # 事件循环引用
        
    def _on_text_result(self, text: str):
        """ASR 识别结果回调"""
        if text:
            # 显示识别结果
            print(f"{Fore.WHITE}[识别] {text}{Style.RESET_ALL}")
            
            # 累积文本并检查关键词
            self.text_buffer += text
            
            # 发送到 Web 客户端（线程安全方式）
            self._schedule_async(self.web_server.send_recognition(text))
            
            # 检查关键词
            detected = self.keyword_alert.check_and_alert(self.text_buffer)
            
            # 如果触发了报警，通知 Web 客户端并清空缓冲区
            if detected:
                keywords = [kw for kw in config.keywords if kw in self.text_buffer]
                self._schedule_async(self.web_server.send_alert(keywords, text))
                # 清空缓冲区，避免同一内容重复触发
                self.text_buffer = ""
            
            # 保持缓冲区在合理长度（避免内存无限增长）
            elif len(self.text_buffer) > 500:
                self.text_buffer = self.text_buffer[-200:]
    
    def _schedule_async(self, coro):
        """线程安全地调度异步任务"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)
    
    def _on_audio_data(self, audio_data: bytes):
        """音频数据回调（来自 WebSocket）"""
        if self.is_running:
            self.asr_engine.feed_audio(audio_data)
    
    async def _handle_restart(self):
        """处理重启请求"""
        print(f"{Fore.YELLOW}[信息] 收到重启请求...{Style.RESET_ALL}")
        self._restart_requested = True
        await self.stop_async()
    
    async def start_async(self):
        """异步启动监听"""
        # 保存事件循环引用（用于线程安全调度）
        self._loop = asyncio.get_running_loop()
        
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
            
            # 启动 Web 控制面板
            await self.web_server.start()
            
            self.is_running = True
            
            print(f"\n{Fore.GREEN}系统已就绪，等待浏览器插件连接...{Style.RESET_ALL}")
            print(f"{Fore.CYAN}监控关键词: {', '.join(config.keywords)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}按 Ctrl+C 停止服务{Style.RESET_ALL}\n")
            
            # 启动 WebSocket 服务器（异步）
            await self.ws_server.start_async()
                
        except asyncio.CancelledError:
            print(f"\n{Fore.YELLOW}收到停止信号...{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[错误] 运行时错误: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
        finally:
            await self.stop_async()
    
    async def stop_async(self):
        """异步停止监听"""
        self.is_running = False
        
        print(f"\n{Fore.CYAN}正在停止系统...{Style.RESET_ALL}")
        
        # 停止 WebSocket 服务器
        try:
            await self.ws_server.stop_async()
        except:
            pass
        
        # 停止 Web 服务器
        try:
            await self.web_server.stop()
        except:
            pass
        
        # 停止 ASR 引擎
        try:
            self.asr_engine.stop()
        except:
            pass
        
        print(f"{Fore.GREEN}系统已安全停止{Style.RESET_ALL}")
    
    def start(self):
        """启动监听（同步入口）"""
        while True:
            self._restart_requested = False
            
            try:
                asyncio.run(self.start_async())
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}收到停止信号...{Style.RESET_ALL}")
                break
            
            # 如果是重启请求，重新初始化并启动
            if self._restart_requested:
                print(f"{Fore.CYAN}[信息] 正在重启服务...{Style.RESET_ALL}")
                # 重新初始化
                self.__init__()
            else:
                break
    
    def stop(self):
        """停止监听（同步入口）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.stop_async())
            else:
                asyncio.run(self.stop_async())
        except:
            pass
