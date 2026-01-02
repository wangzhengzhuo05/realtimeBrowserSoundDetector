# -*- coding: utf-8 -*-
"""
ASR 引擎抽象基类
"""

from abc import ABC, abstractmethod
from typing import Callable


class ASREngine(ABC):
    """ASR 语音识别引擎的抽象基类"""
    
    @abstractmethod
    def start(self):
        """启动识别引擎"""
        pass
    
    @abstractmethod
    def feed_audio(self, audio_data: bytes):
        """输入音频数据进行识别"""
        pass
    
    @abstractmethod
    def stop(self):
        """停止识别引擎"""
        pass
    
    @abstractmethod
    def set_result_callback(self, callback: Callable[[str], None]):
        """设置识别结果回调函数"""
        pass
