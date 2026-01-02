# -*- coding: utf-8 -*-
"""
Qwen2-Audio 语音理解检测模块
直接使用多模态大模型理解语音内容并检测关键词
"""

import os
import time
import tempfile
import threading
import wave
from typing import List, Optional, Callable
from colorama import Fore, Style

try:
    from dashscope import MultiModalConversation
except ImportError:
    MultiModalConversation = None
    print(f"{Fore.YELLOW}[警告] 请安装 dashscope: pip install dashscope{Style.RESET_ALL}")


class Qwen2AudioDetector:
    """
    Qwen2-Audio 语音理解检测器
    直接用音频问模型是否包含关键词
    """
    
    def __init__(self, api_key: str, keywords: List[str], cooldown: int = 5,
                 sample_rate: int = 16000, channels: int = 1):
        """
        :param api_key: DashScope API Key
        :param keywords: 关键词列表
        :param cooldown: 报警冷却时间（秒）
        :param sample_rate: 音频采样率
        :param channels: 音频通道数
        """
        self.api_key = api_key
        self.keywords = keywords
        self.cooldown = cooldown
        self.sample_rate = sample_rate
        self.channels = channels
        
        self.enabled = False
        self.last_alert_time = 0
        self.lock = threading.Lock()
        
        # 音频缓冲（累积一定时长后检测）
        self.audio_buffer = b""
        self.buffer_lock = threading.Lock()
        self.buffer_duration = 4.0  # 每 4 秒检测一次
        self.bytes_per_second = sample_rate * channels * 2  # 16-bit PCM
        self.buffer_size = int(self.buffer_duration * self.bytes_per_second)
        
        # 检测回调
        self.alert_callback: Optional[Callable[[List[str], str], None]] = None
        self.text_callback: Optional[Callable[[str], None]] = None
        
        # 后台检测线程
        self._running = False
        self._detect_thread: Optional[threading.Thread] = None
        
        if not MultiModalConversation:
            print(f"{Fore.YELLOW}[警告] DashScope 未安装，Qwen2-Audio 检测已禁用{Style.RESET_ALL}")
            return
        
        if not api_key:
            print(f"{Fore.YELLOW}[警告] API Key 未配置，Qwen2-Audio 检测已禁用{Style.RESET_ALL}")
            return
        
        self.enabled = True
        print(f"{Fore.GREEN}[Qwen2-Audio] 检测器已初始化，缓冲时长: {self.buffer_duration}秒{Style.RESET_ALL}")
    
    def set_alert_callback(self, callback: Callable[[List[str], str], None]):
        """设置报警回调"""
        self.alert_callback = callback
    
    def set_text_callback(self, callback: Callable[[str], None]):
        """设置文本识别回调（用于显示识别内容）"""
        self.text_callback = callback
    
    def feed_audio(self, audio_data: bytes):
        """接收音频数据"""
        if not self.enabled:
            return
        
        with self.buffer_lock:
            self.audio_buffer += audio_data
    
    def start(self):
        """启动后台检测"""
        if not self.enabled:
            return
        
        self._running = True
        self._detect_thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._detect_thread.start()
        print(f"{Fore.CYAN}[Qwen2-Audio] 后台检测已启动{Style.RESET_ALL}")
    
    def stop(self):
        """停止检测"""
        self._running = False
        if self._detect_thread:
            self._detect_thread.join(timeout=2)
        print(f"{Fore.CYAN}[Qwen2-Audio] 检测已停止{Style.RESET_ALL}")
    
    def _detect_loop(self):
        """后台检测循环"""
        while self._running:
            # 检查缓冲区是否有足够数据
            with self.buffer_lock:
                if len(self.audio_buffer) < self.buffer_size:
                    time.sleep(0.5)
                    continue
                
                # 取出一段音频
                audio_chunk = self.audio_buffer[:self.buffer_size]
                self.audio_buffer = self.audio_buffer[self.buffer_size:]
            
            # 检测这段音频
            try:
                self._detect_audio(audio_chunk)
            except Exception as e:
                print(f"{Fore.YELLOW}[Qwen2-Audio] 检测异常: {e}{Style.RESET_ALL}")
    
    def _detect_audio(self, audio_data: bytes):
        """检测音频片段"""
        # 保存为临时 WAV 文件
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data)
            
            # 调用 Qwen2-Audio 分析
            result = self._call_qwen2_audio(temp_file.name)
            
            if result:
                detected_keywords, transcription = result
                
                # 显示识别文本
                if transcription and self.text_callback:
                    self.text_callback(transcription)
                
                # 触发报警
                if detected_keywords:
                    self._trigger_alert(detected_keywords, transcription or "")
        
        finally:
            # 清理临时文件
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
    
    def _call_qwen2_audio(self, audio_path: str) -> Optional[tuple]:
        """
        调用 Qwen2-Audio 分析音频
        返回 (检测到的关键词列表, 识别的文本) 或 None
        """
        keywords_str = "、".join(self.keywords)
        prompt = f"""请分析这段语音，完成以下任务：
1. 转录语音内容
2. 判断语音中是否提到了以下关键词或其同义表达：{keywords_str}

请按以下格式回答：
转录：<语音内容>
关键词：<检测到的关键词，用逗号分隔，如果没有检测到则填"无">"""

        try:
            # 上传音频文件
            from dashscope import MultiModalConversation
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"audio": f"file://{audio_path}"},
                        {"text": prompt}
                    ]
                }
            ]
            
            response = MultiModalConversation.call(
                model="qwen2-audio-instruct",
                messages=messages,
                api_key=self.api_key
            )
            
            if response.status_code != 200:
                print(f"{Fore.YELLOW}[Qwen2-Audio] API 调用失败: {response.message}{Style.RESET_ALL}")
                return None
            
            # 解析回复
            content = response.output.get("choices", [{}])[0].get("message", {}).get("content", [])
            text_response = ""
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_response = item["text"]
                    break
                elif isinstance(item, str):
                    text_response = item
                    break
            
            if not text_response:
                return None
            
            # 解析转录和关键词
            transcription = ""
            detected = []
            
            for line in text_response.split("\n"):
                line = line.strip()
                if line.startswith("转录：") or line.startswith("转录:"):
                    transcription = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif line.startswith("关键词：") or line.startswith("关键词:"):
                    kw_text = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                    if kw_text and kw_text != "无":
                        detected = [k.strip() for k in kw_text.replace("，", ",").split(",") if k.strip()]
            
            return (detected, transcription)
            
        except Exception as e:
            print(f"{Fore.YELLOW}[Qwen2-Audio] 分析异常: {e}{Style.RESET_ALL}")
            return None
    
    def _trigger_alert(self, keywords: List[str], text: str):
        """触发报警"""
        # 检查冷却
        with self.lock:
            current_time = time.time()
            if self.cooldown > 0 and current_time - self.last_alert_time < self.cooldown:
                return
            self.last_alert_time = current_time
        
        print(f"\n{Fore.RED}{'!'*60}")
        print(f"{'!'*20} Qwen2-Audio 检测到关键词 {'!'*20}")
        print(f"{'!'*60}")
        print(f"\n  关键词: {', '.join(keywords)}")
        print(f"  内容: {text[:100] if len(text) > 100 else text}")
        print(f"\n{'!'*60}{Style.RESET_ALL}\n")
        
        # 播放报警音
        try:
            import winsound
            threading.Thread(target=self._play_alert, daemon=True).start()
        except:
            pass
        
        # 回调
        if self.alert_callback:
            self.alert_callback(keywords, text)
    
    def _play_alert(self):
        """播放报警音"""
        try:
            import winsound
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            time.sleep(0.3)
            for _ in range(3):
                winsound.Beep(1200, 200)
                winsound.Beep(800, 200)
        except:
            pass
    
    def update_keywords(self, keywords: List[str]):
        """更新关键词"""
        self.keywords = keywords
        print(f"{Fore.CYAN}[Qwen2-Audio] 关键词已更新: {', '.join(keywords)}{Style.RESET_ALL}")
