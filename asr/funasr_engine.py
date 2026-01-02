# -*- coding: utf-8 -*-
"""
本地 FunASR 实时语音识别引擎
使用 Paraformer-zh-streaming 模型，支持 GPU 加速
"""

import time
import threading
from typing import Callable

import numpy as np
from colorama import Fore, Style

from .base import ASREngine
from config import SAMPLE_RATE


class FunASREngine(ASREngine):
    """
    本地 FunASR 实时语音识别引擎
    使用 Paraformer-zh-streaming 模型，支持 GPU 加速
    """
    
    def __init__(self):
        self.model = None
        self.result_callback = None
        self.audio_buffer = []
        self.is_running = False
        self.process_thread = None
        self.cache = {}  # 流式识别的缓存状态
        
    def set_result_callback(self, callback: Callable[[str], None]):
        """设置识别结果回调函数"""
        self.result_callback = callback
    
    def start(self):
        """启动 FunASR 本地识别"""
        try:
            from funasr import AutoModel
            import torch
            
            # 检测 GPU 可用性
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"{Fore.CYAN}[信息] FunASR 使用设备: {device}{Style.RESET_ALL}")
            
            if device == "cpu":
                print(f"{Fore.YELLOW}[警告] 未检测到 CUDA GPU，将使用 CPU 运行（速度较慢）{Style.RESET_ALL}")
            
            # 加载流式识别模型
            print(f"{Fore.CYAN}[信息] 正在加载 FunASR 模型，首次运行需要下载...{Style.RESET_ALL}")
            
            self.model = AutoModel(
                model="paraformer-zh-streaming",
                device=device,
                disable_update=True  # 禁用自动更新检查
            )
            
            self.is_running = True
            self.cache = {}
            
            # 启动处理线程
            self.audio_buffer = []
            self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
            self.process_thread.start()
            
            print(f"{Fore.GREEN}[成功] FunASR 本地识别已启动{Style.RESET_ALL}")
            
        except ImportError as e:
            print(f"{Fore.RED}[错误] 请安装 FunASR 相关库:{Style.RESET_ALL}")
            print(f"  pip install funasr torch torchaudio modelscope")
            raise
        except Exception as e:
            print(f"{Fore.RED}[错误] 启动 FunASR 失败: {e}{Style.RESET_ALL}")
            raise
    
    def feed_audio(self, audio_data: bytes):
        """将音频数据加入缓冲区"""
        if self.is_running:
            # 将 bytes 转换为 numpy 数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            self.audio_buffer.append(audio_array)
    
    def _process_loop(self):
        """后台线程：处理音频缓冲区中的数据"""
        chunk_samples = SAMPLE_RATE // 10 * 6  # 600ms 的数据
        accumulated = np.array([], dtype=np.int16)
        
        while self.is_running:
            try:
                # 收集缓冲区中的数据
                if self.audio_buffer:
                    while self.audio_buffer:
                        accumulated = np.concatenate([accumulated, self.audio_buffer.pop(0)])
                
                # 当积累够一定量的数据时进行识别
                if len(accumulated) >= chunk_samples:
                    # 取出一段数据进行识别
                    chunk = accumulated[:chunk_samples]
                    accumulated = accumulated[chunk_samples:]
                    
                    # 转换为浮点数 (FunASR 需要)
                    audio_float = chunk.astype(np.float32) / 32768.0
                    
                    # 流式识别
                    result = self.model.generate(
                        input=audio_float,
                        cache=self.cache,
                        is_final=False,
                        chunk_size=[0, 10, 5],  # 流式配置
                        encoder_chunk_look_back=4,
                        decoder_chunk_look_back=1
                    )
                    
                    if result and len(result) > 0:
                        text = result[0].get('text', '')
                        if text and self.result_callback:
                            self.result_callback(text)
                else:
                    time.sleep(0.05)  # 避免空转
                    
            except Exception as e:
                print(f"{Fore.YELLOW}[警告] FunASR 处理出错: {e}{Style.RESET_ALL}")
                time.sleep(0.1)
    
    def stop(self):
        """停止 FunASR 识别"""
        self.is_running = False
        if self.process_thread:
            self.process_thread.join(timeout=2)
        print(f"{Fore.CYAN}[信息] FunASR 识别已停止{Style.RESET_ALL}")
