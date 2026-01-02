# -*- coding: utf-8 -*-
"""
课堂监听主控制器 (Web 增强版)
协调 WebSocket 服务器、ASR 识别、关键词报警和 Web 控制面板
支持三种检测模式：ASR+关键词、ASR+LLM语义检测、Qwen2-Audio大模型
"""

import asyncio
from typing import Optional, List

from colorama import Fore, Style

from config_manager import config
from audio import AudioWebSocketServer
from asr import DashScopeASR, FunASREngine
from alert import KeywordAlert, Qwen2AudioDetector, LLMTextDetector
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
        self.detect_mode = config.detect_mode  # "asr" 或 "qwen2-audio"
        self.debug_mode = config.debug_mode    # 同时运行 ASR 和 Qwen2-Audio
        self.mute_playback = config.mute_playback  # 是否静音外放
        
        # 初始化 WebSocket 服务器（接收浏览器音频）
        self.ws_server = AudioWebSocketServer(config.ws_host, config.ws_port)
        
        # 根据检测模式初始化
        self.keyword_alert = None
        self.asr_engine = None
        self.audio_detector = None
        self.llm_detector = None  # LLM 文本语义检测器
        
        # Debug 模式：同时运行 ASR 和 Qwen2-Audio
        if self.debug_mode:
            print(f"{Fore.YELLOW}[DEBUG] 调试模式：同时运行 ASR 和 Qwen2-Audio{Style.RESET_ALL}")
            
            # 初始化 ASR + 关键词
            self.keyword_alert = KeywordAlert(
                keywords=config.keywords, 
                cooldown=config.cooldown, 
                custom_sound=config.custom_sound,
                api_key=config.api_key,
                enable_semantic=config.enable_semantic,
                semantic_threshold=config.semantic_threshold,
                semantic_model=config.semantic_model
            )
            
            if self.use_cloud_api:
                print(f"{Fore.CYAN}[信息] ASR: 阿里云 DashScope API{Style.RESET_ALL}")
                self.asr_engine = DashScopeASR(config.api_key)
            else:
                print(f"{Fore.CYAN}[信息] ASR: 本地 FunASR{Style.RESET_ALL}")
                self.asr_engine = FunASREngine()
            
            # 同时初始化 Qwen2-Audio
            print(f"{Fore.MAGENTA}[信息] Qwen2-Audio: 大模型语音理解{Style.RESET_ALL}")
            self.audio_detector = Qwen2AudioDetector(
                api_key=config.api_key,
                keywords=config.keywords,
                cooldown=0  # Debug 模式下不限制冷却，方便对比
            )
            
        elif self.detect_mode == "qwen2-audio":
            # Qwen2-Audio 大模型模式
            print(f"{Fore.MAGENTA}[模式] 使用 Qwen2-Audio 大模型语音理解{Style.RESET_ALL}")
            self.audio_detector = Qwen2AudioDetector(
                api_key=config.api_key,
                keywords=config.keywords,
                cooldown=config.cooldown
            )
            
        elif self.detect_mode == "asr+llm":
            # ASR + LLM 混合模式：ASR 实时转文字 + 关键词检测，LLM 每3秒进行语义检测
            print(f"{Fore.GREEN}[模式] 使用 ASR + LLM 语义检测（混合模式）{Style.RESET_ALL}")
            
            # 初始化 ASR 引擎
            if self.use_cloud_api:
                print(f"{Fore.CYAN}[信息] ASR: 阿里云 DashScope API{Style.RESET_ALL}")
                self.asr_engine = DashScopeASR(config.api_key)
            else:
                print(f"{Fore.CYAN}[信息] ASR: 本地 FunASR{Style.RESET_ALL}")
                self.asr_engine = FunASREngine()
            
            # 初始化关键词报警（用于 ASR 精确匹配）
            self.keyword_alert = KeywordAlert(
                keywords=config.keywords, 
                cooldown=config.cooldown, 
                custom_sound=config.custom_sound,
                api_key=config.api_key,
                enable_semantic=False,  # 混合模式不用语义匹配，由 LLM 负责
                semantic_threshold=config.semantic_threshold,
                semantic_model=config.semantic_model
            )
            
            # 初始化 LLM 文本检测器
            llm_interval = getattr(config, 'llm_detect_interval', 3.0)
            llm_model = getattr(config, 'llm_model', 'qwen-turbo')
            print(f"{Fore.GREEN}[信息] LLM 检测: 每 {llm_interval} 秒检测一次 (模型: {llm_model}){Style.RESET_ALL}")
            
            self.llm_detector = LLMTextDetector(
                api_key=config.api_key,
                keywords=config.keywords,
                interval=llm_interval,
                cooldown=config.cooldown,
                model=llm_model
            )
            
        else:
            # 传统 ASR + 关键词模式
            print(f"{Fore.CYAN}[模式] 使用 ASR + 关键词匹配{Style.RESET_ALL}")
            
            # 初始化关键词报警（支持自定义报警音频和语义匹配）
            self.keyword_alert = KeywordAlert(
                keywords=config.keywords, 
                cooldown=config.cooldown, 
                custom_sound=config.custom_sound,
                api_key=config.api_key,
                enable_semantic=config.enable_semantic,
                semantic_threshold=config.semantic_threshold,
                semantic_model=config.semantic_model
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
        """ASR 识别结果回调（仅 ASR 模式使用）"""
        if text:
            # 显示识别结果
            label = "[ASR]" if self.debug_mode else "[识别]"
            print(f"{Fore.WHITE}{label} {text}{Style.RESET_ALL}")
            
            # 累积文本并检查关键词
            self.text_buffer += text
            
            # 发送到 Web 客户端（线程安全方式）
            source = "asr" if self.debug_mode else None
            self._schedule_async(self.web_server.send_recognition(text, source))
            
            # 检查关键词
            detected = self.keyword_alert.check_and_alert(self.text_buffer)
            
            # 如果触发了报警，通知 Web 客户端并清空缓冲区
            if detected:
                keywords = [kw for kw in config.keywords if kw in self.text_buffer]
                self._schedule_async(self.web_server.send_alert(keywords, text, source))
                # 清空缓冲区，避免同一内容重复触发
                self.text_buffer = ""
            
            # 保持缓冲区在合理长度（避免内存无限增长）
            elif len(self.text_buffer) > 500:
                self.text_buffer = self.text_buffer[-200:]
    
    def _on_qwen2_text(self, text: str):
        """Qwen2-Audio 文本识别回调"""
        if text:
            # Debug 模式下用不同颜色区分
            label = "[Qwen2-Audio]" if self.debug_mode else "[识别]"
            print(f"{Fore.MAGENTA}{label} {text}{Style.RESET_ALL}")
            # 发送识别结果
            source = "qwen2-audio" if self.debug_mode else None
            self._schedule_async(self.web_server.send_recognition(text, source))
    
    def _on_qwen2_alert(self, keywords: List[str], text: str):
        """Qwen2-Audio 报警回调"""
        source = "qwen2-audio" if self.debug_mode else None
        if self.debug_mode:
            # Debug 模式下也发送报警（用于对比）
            print(f"{Fore.MAGENTA}[Qwen2-Audio 检测] 关键词: {', '.join(keywords)}{Style.RESET_ALL}")
            self._schedule_async(self.web_server.send_alert(keywords, text, source))
        else:
            self._schedule_async(self.web_server.send_alert(keywords, text, source))
    
    def _on_asr_llm_text(self, text: str):
        """ASR+LLM 模式的 ASR 识别结果回调"""
        if text:
            print(f"{Fore.WHITE}[识别] {text}{Style.RESET_ALL}")
            
            # 累积文本
            self.text_buffer += text
            
            # 发送到 Web 客户端显示
            self._schedule_async(self.web_server.send_recognition(text, None))
            
            # 1. ASR 关键词检测（精确匹配）
            if self.keyword_alert:
                detected = self.keyword_alert.check_and_alert(self.text_buffer)
                if detected:
                    keywords = [kw for kw in config.keywords if kw in self.text_buffer]
                    print(f"{Fore.YELLOW}[ASR报警] 关键词: {', '.join(keywords)}{Style.RESET_ALL}")
                    self._schedule_async(self.web_server.send_alert(keywords, text, "asr"))
                    # 清空缓冲区，避免重复触发
                    self.text_buffer = ""
            
            # 2. 同时喂给 LLM 检测器（语义检测）
            if self.llm_detector:
                self.llm_detector.feed_text(text)
            
            # 保持缓冲区在合理长度
            if len(self.text_buffer) > 500:
                self.text_buffer = self.text_buffer[-200:]
    
    def _on_llm_alert(self, keywords: List[str], text: str):
        """LLM 语义检测报警回调"""
        print(f"{Fore.GREEN}[LLM报警] 检测到意图: {', '.join(keywords)}{Style.RESET_ALL}")
        self._schedule_async(self.web_server.send_alert(keywords, text, "llm"))
        
        # 播放报警音
        import winsound
        try:
            winsound.Beep(1000, 500)
        except:
            pass
    
    def _schedule_async(self, coro):
        """线程安全地调度异步任务"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)
    
    def _on_audio_data(self, audio_data: bytes):
        """音频数据回调（来自 WebSocket）"""
        if self.is_running:
            # Debug 模式：同时送给两个引擎
            if self.debug_mode:
                if self.asr_engine:
                    self.asr_engine.feed_audio(audio_data)
                if self.audio_detector:
                    self.audio_detector.feed_audio(audio_data)
            elif self.detect_mode == "qwen2-audio" and self.audio_detector:
                # Qwen2-Audio 模式：直接送给大模型
                self.audio_detector.feed_audio(audio_data)
            elif self.detect_mode == "asr+llm" and self.asr_engine:
                # ASR+LLM 模式：送给 ASR 引擎（LLM 检测器从 ASR 结果获取文本）
                self.asr_engine.feed_audio(audio_data)
            elif self.asr_engine:
                # 传统 ASR 模式：送给 ASR 引擎
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
            # Debug 模式：同时启动两个引擎
            if self.debug_mode:
                if self.asr_engine:
                    self.asr_engine.set_result_callback(self._on_text_result)
                    self.asr_engine.start()
                if self.audio_detector:
                    self.audio_detector.set_text_callback(self._on_qwen2_text)
                    self.audio_detector.set_alert_callback(self._on_qwen2_alert)
                    self.audio_detector.start()
            elif self.detect_mode == "asr+llm" and self.asr_engine and self.llm_detector:
                # ASR+LLM 模式：启动 ASR 和 LLM 检测器
                self.asr_engine.set_result_callback(self._on_asr_llm_text)
                self.asr_engine.start()
                self.llm_detector.set_alert_callback(self._on_llm_alert)
                self.llm_detector.start()
            elif self.detect_mode == "qwen2-audio" and self.audio_detector:
                # Qwen2-Audio 模式
                self.audio_detector.set_text_callback(self._on_qwen2_text)
                self.audio_detector.set_alert_callback(self._on_qwen2_alert)
                self.audio_detector.start()
            elif self.asr_engine:
                # ASR 模式
                self.asr_engine.set_result_callback(self._on_text_result)
                self.asr_engine.start()
            
            # 设置 WebSocket 音频回调
            self.ws_server.set_audio_callback(self._on_audio_data)
            
            # 启动 Web 控制面板
            await self.web_server.start()
            
            self.is_running = True
            
            mode_info = "DEBUG (ASR + Qwen2-Audio)" if self.debug_mode else self.detect_mode
            print(f"\n{Fore.GREEN}系统已就绪，等待浏览器插件连接...{Style.RESET_ALL}")
            print(f"{Fore.CYAN}检测模式: {mode_info}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}监控关键词: {', '.join(config.keywords)}{Style.RESET_ALL}")
            if self.mute_playback:
                print(f"{Fore.YELLOW}静音模式: 已开启{Style.RESET_ALL}")
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
        
        # 停止 ASR 引擎或 Audio 检测器
        try:
            if self.asr_engine:
                self.asr_engine.stop()
            if self.audio_detector:
                self.audio_detector.stop()
            if self.llm_detector:
                self.llm_detector.stop()
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
