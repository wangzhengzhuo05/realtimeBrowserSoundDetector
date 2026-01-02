# -*- coding: utf-8 -*-
"""
ASR 语音识别引擎模块
"""

from .base import ASREngine
from .dashscope_asr import DashScopeASR
from .funasr_engine import FunASREngine

__all__ = ['ASREngine', 'DashScopeASR', 'FunASREngine']
