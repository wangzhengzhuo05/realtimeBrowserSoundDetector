# -*- coding: utf-8 -*-
"""
阿里云 DashScope 实时语音识别引擎
使用 Paraformer-Realtime 模型进行流式识别
"""

import threading
import queue
import time
from typing import Callable
from colorama import Fore, Style

from .base import ASREngine
from config import SAMPLE_RATE


class DashScopeASR(ASREngine):
    """
    阿里云 DashScope 实时语音识别引擎
    使用 Paraformer-Realtime 模型进行流式识别
    支持自动重连
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.recognition = None
        self.result_callback = None
        self.is_running = False
        self.audio_queue = queue.Queue()
        self.recognition_thread = None
        self.reconnect_count = 0
        self.max_reconnect = 10  # 最大重连次数
        self.connection_alive = False
        
    def set_result_callback(self, callback: Callable[[str], None]):
        """设置识别结果回调函数"""
        self.result_callback = callback
    
    def _create_recognition(self):
        """创建识别对象"""
        import dashscope
        from dashscope.audio.asr import Recognition, RecognitionCallback
        
        # 设置 API Key
        dashscope.api_key = self.api_key
        
        # 保存外部引用
        parent = self
        
        # 创建回调类
        class MyRecognitionCallback(RecognitionCallback):
            def on_open(self):
                parent.connection_alive = True
                parent.reconnect_count = 0  # 重置重连计数
                print(f"{Fore.GREEN}[成功] DashScope 实时识别已连接{Style.RESET_ALL}")
            
            def on_complete(self):
                parent.connection_alive = False
                print(f"{Fore.CYAN}[信息] DashScope 识别完成{Style.RESET_ALL}")
            
            def on_error(self, result):
                parent.connection_alive = False
                print(f"{Fore.RED}[错误] DashScope ASR 错误: {result}{Style.RESET_ALL}")
            
            def on_close(self):
                parent.connection_alive = False
                print(f"{Fore.CYAN}[信息] DashScope 连接已关闭{Style.RESET_ALL}")
            
            def on_event(self, result):
                # 处理识别结果
                if parent.result_callback and result:
                    try:
                        # 获取识别文本
                        sentence = result.get_sentence()
                        if sentence and 'text' in sentence:
                            text = sentence['text']
                            if text:
                                parent.result_callback(text)
                    except Exception as e:
                        print(f"{Fore.YELLOW}[警告] 解析识别结果时出错: {e}{Style.RESET_ALL}")
        
        # 创建回调实例
        callback = MyRecognitionCallback()
        
        # 创建实时识别对象
        self.recognition = Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=SAMPLE_RATE,
            callback=callback
        )
        
        # 启动识别
        self.recognition.start()
        self.connection_alive = True
        
    def _recognition_worker(self):
        """识别工作线程 - 支持自动重连"""
        try:
            # 首次创建识别
            self._create_recognition()
            self.is_running = True
            print(f"{Fore.GREEN}[成功] DashScope 实时识别已启动{Style.RESET_ALL}")
            
            # 持续发送音频数据
            while self.is_running:
                try:
                    audio_data = self.audio_queue.get(timeout=0.1)
                    
                    if audio_data and self.recognition and self.connection_alive:
                        try:
                            self.recognition.send_audio_frame(audio_data)
                        except Exception as e:
                            error_msg = str(e)
                            if "stopped" in error_msg.lower() or "closed" in error_msg.lower():
                                # 连接断开，需要重连
                                self.connection_alive = False
                                if self.is_running and self.reconnect_count < self.max_reconnect:
                                    self._reconnect()
                            else:
                                print(f"{Fore.YELLOW}[警告] 发送音频数据失败: {e}{Style.RESET_ALL}")
                    elif audio_data and not self.connection_alive and self.is_running:
                        # 连接断开，尝试重连
                        if self.reconnect_count < self.max_reconnect:
                            self._reconnect()
                        
                except queue.Empty:
                    continue
            
            # 停止识别
            if self.recognition:
                try:
                    self.recognition.stop()
                except:
                    pass
                
        except ImportError:
            print(f"{Fore.RED}[错误] 请安装 dashscope 库: pip install dashscope{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[错误] DashScope 识别线程错误: {e}{Style.RESET_ALL}")
    
    def _reconnect(self):
        """重新连接 DashScope"""
        self.reconnect_count += 1
        print(f"{Fore.YELLOW}[重连] 正在重新连接 DashScope (第 {self.reconnect_count}/{self.max_reconnect} 次)...{Style.RESET_ALL}")
        
        # 停止旧连接
        if self.recognition:
            try:
                self.recognition.stop()
            except:
                pass
            self.recognition = None
        
        # 等待一下再重连
        time.sleep(1)
        
        # 清空队列中积压的旧数据
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break
        
        try:
            self._create_recognition()
            print(f"{Fore.GREEN}[成功] DashScope 重连成功{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[错误] DashScope 重连失败: {e}{Style.RESET_ALL}")
            self.connection_alive = False
    
    def start(self):
        """启动 DashScope 实时识别"""
        # 在新线程中启动识别
        self.recognition_thread = threading.Thread(target=self._recognition_worker, daemon=True)
        self.recognition_thread.start()
    
    def feed_audio(self, audio_data: bytes):
        """发送音频数据到队列"""
        if self.is_running:
            # 限制队列大小，避免积压过多
            if self.audio_queue.qsize() < 100:
                self.audio_queue.put(audio_data)
    
    def stop(self):
        """停止 DashScope 识别"""
        self.is_running = False
        self.connection_alive = False
        if self.recognition_thread:
            self.recognition_thread.join(timeout=3)
        print(f"{Fore.CYAN}[信息] DashScope 识别已停止{Style.RESET_ALL}")
