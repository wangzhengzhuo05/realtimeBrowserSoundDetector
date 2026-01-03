# -*- coding: utf-8 -*-
"""
关键词检测与报警模块
检测识别文本中的关键词并触发报警
支持精确匹配和语义模糊匹配
"""

import time
import threading
import winsound
import os
import os.path
from pathlib import Path
from typing import List, Optional

from colorama import Fore, Style

from .semantic_matcher import SemanticMatcher

# 项目根目录（用于解析相对路径）
PROJECT_ROOT = Path(__file__).parent.parent

# 可选的多格式播放支持（mp3/ogg/m4a/flac 等依赖系统解码能力）
try:
    from playsound import playsound  # type: ignore
    PLAYSOUND_AVAILABLE = True
except ImportError:
    PLAYSOUND_AVAILABLE = False


class KeywordAlert:
    """
    关键词检测与报警模块
    检测识别文本中的关键词并触发报警
    支持精确匹配和语义模糊匹配
    """
    
    def __init__(self, keywords: List[str], cooldown: int = 10, custom_sound: str = None,
                 api_key: str = None, enable_semantic: bool = False, semantic_threshold: float = 0.65,
                 semantic_model: str = "text-embedding-v3"):
        """
        :param keywords: 关键词列表
        :param cooldown: 报警冷却时间（秒）
        :param custom_sound: 自定义报警音频文件路径（默认支持 .wav；安装 playsound 后可播放 mp3/ogg/m4a/flac 等）
        :param api_key: DashScope API Key（语义匹配需要）
        :param enable_semantic: 是否启用语义匹配
        :param semantic_threshold: 语义相似度阈值 (0-1)
        """
        self.keywords = keywords
        self.cooldown = cooldown
        self.custom_sound = None
        self.last_alert_time = 0
        self.lock = threading.Lock()
        self.enable_semantic = enable_semantic
        self.semantic_matcher: Optional[SemanticMatcher] = None
        
        # 验证并设置自定义音频文件
        self._set_custom_sound(custom_sound)
        
        # 初始化语义匹配器
        if enable_semantic and api_key:
            self.semantic_matcher = SemanticMatcher(api_key, keywords, semantic_threshold, semantic_model)
    
    def _resolve_sound_path(self, sound_path: str) -> Optional[str]:
        """
        解析音频文件路径，支持绝对路径和相对路径
        :param sound_path: 原始路径（可以是绝对路径或相对于项目根目录的路径）
        :return: 有效的绝对路径，如果文件不存在则返回 None
        """
        if not sound_path:
            return None
        
        # 1. 首先尝试作为绝对路径
        if os.path.isabs(sound_path) and os.path.exists(sound_path):
            return sound_path
        
        # 2. 尝试作为相对路径（相对于项目根目录）
        relative_path = PROJECT_ROOT / sound_path
        if relative_path.exists():
            return str(relative_path)
        
        # 3. 如果路径包含 assets/custom_sounds，尝试提取文件名并在默认目录查找
        if "custom_sounds" in sound_path:
            filename = os.path.basename(sound_path)
            default_path = PROJECT_ROOT / "assets" / "custom_sounds" / filename
            if default_path.exists():
                return str(default_path)
        
        # 4. 路径无效
        return None
    
    def _set_custom_sound(self, custom_sound: str = None):
        """
        设置并验证自定义音频文件
        :param custom_sound: 音频文件路径
        """
        if not custom_sound:
            self.custom_sound = None
            return
        
        resolved_path = self._resolve_sound_path(custom_sound)
        if resolved_path:
            self.custom_sound = resolved_path
            print(f"{Fore.GREEN}[信息] 已加载自定义报警音频: {self.custom_sound}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}[警告] 自定义音频文件不存在: {custom_sound}，将使用默认蜂鸣声{Style.RESET_ALL}")
            self.custom_sound = None

    def update_sound(self, custom_sound: str = None):
        """
        动态更新报警音源
        :param custom_sound: 新的自定义音频文件路径，None 或空字符串表示使用默认蜂鸣声
        """
        old_sound = self.custom_sound
        
        if custom_sound:
            # 使用路径解析逻辑
            self._set_custom_sound(custom_sound)
            if self.custom_sound:
                print(f"{Fore.GREEN}[信息] 报警音源已更新: {self.custom_sound}{Style.RESET_ALL}")
        else:
            self.custom_sound = None
            if old_sound:
                print(f"{Fore.CYAN}[信息] 报警音源已切换为默认蜂鸣声{Style.RESET_ALL}")
        
    def check_and_alert(self, text: str) -> bool:
        """
        检查文本中是否包含关键词，如果包含则触发报警
        支持精确匹配和语义模糊匹配
        :param text: 识别的文本
        :return: 是否触发了报警
        """
        if not text:
            return False
        
        detected_keywords = []
        is_semantic_match = False
        
        # 1. 精确匹配检查
        for keyword in self.keywords:
            if keyword in text:
                detected_keywords.append(keyword)
        
        # 2. 语义模糊匹配（如果精确匹配未命中且启用了语义匹配）
        if not detected_keywords and self.semantic_matcher and self.semantic_matcher.enabled:
            # 只对最近的文本进行语义匹配（避免重复匹配）
            recent_text = text[-50:] if len(text) > 50 else text
            semantic_matches = self.semantic_matcher.find_similar_keywords(recent_text)
            if semantic_matches:
                detected_keywords = [kw for kw, _ in semantic_matches]
                is_semantic_match = True
        
        if not detected_keywords:
            return False
        
        # 检查冷却时间（cooldown为0时不限制）
        with self.lock:
            current_time = time.time()
            if self.cooldown > 0 and current_time - self.last_alert_time < self.cooldown:
                remaining = self.cooldown - (current_time - self.last_alert_time)
                print(f"{Fore.YELLOW}[冷却中] 检测到关键词但在冷却期内，剩余 {remaining:.1f} 秒{Style.RESET_ALL}")
                return False
            
            self.last_alert_time = current_time
        
        # 触发报警
        self._trigger_alert(detected_keywords, text, is_semantic_match)
        return True
    
    def _trigger_alert(self, keywords: List[str], text: str, is_semantic: bool = False):
        """触发报警"""
        # 控制台红色高亮警告
        match_type = "语义匹配" if is_semantic else "精确匹配"
        print(f"\n{Fore.RED}{'!'*60}")
        print(f"{'!'*20} 检测到关键词报警 {'!'*20}")
        print(f"{'!'*60}")
        print(f"\n  匹配类型: {match_type}")
        print(f"  关键词: {', '.join(keywords)}")
        print(f"  原文: {text[-100:] if len(text) > 100 else text}")
        print(f"\n{'!'*60}{Style.RESET_ALL}\n")
        
        # 播放系统提示音 (使用 Windows Beep)
        # 在后台线程中播放，避免阻塞主流程
        threading.Thread(target=self._play_alert_sound, daemon=True).start()
    
    def _play_alert_sound(self):
        """播放报警提示音 - 通过电脑扬声器输出"""
        try:
            # 优先使用自定义音频文件
            if self.custom_sound and os.path.exists(self.custom_sound):
                self._play_custom_sound()
            else:
                self._play_default_beep()
                
        except Exception as e:
            print(f"{Fore.YELLOW}[警告] 播放提示音失败: {e}{Style.RESET_ALL}")
            # 备用方案：使用系统默认提示音
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except:
                pass
    
    def _play_custom_sound(self):
        """播放自定义音频文件"""
        try:
            ext = os.path.splitext(self.custom_sound)[1].lower()

            # 1) WAV 直接用 winsound
            if ext == ".wav":
                winsound.PlaySound(self.custom_sound, winsound.SND_FILENAME)
                return

            # 2) 其他常见格式，尝试 playsound（需要额外安装 playsound）
            if PLAYSOUND_AVAILABLE:
                playsound(self.custom_sound, block=True)
                return

            # 3) 未安装 playsound 时的提示
            print(f"{Fore.YELLOW}[警告] 检测到非 WAV 音频 {self.custom_sound}，请安装 playsound 以支持 mp3/ogg/m4a/flac: pip install playsound{Style.RESET_ALL}")
            self._play_default_beep()
        except Exception as e:
            print(f"{Fore.YELLOW}[警告] 播放自定义音频失败: {e}，使用默认蜂鸣声{Style.RESET_ALL}")
            self._play_default_beep()
    
    def _play_default_beep(self):
        """播放默认蜂鸣声序列"""
        try:
            # 播放 Windows 系统声音（更醒目）
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            time.sleep(0.5)
            
            # 播放蜂鸣声序列（类似警报声）
            # 高低交替的警报音效
            for _ in range(3):
                # 高音
                winsound.Beep(1200, 200)
                # 低音
                winsound.Beep(800, 200)
            
            # 最后播放一个长音提醒
            winsound.Beep(1000, 500)
            
        except Exception as e:
            print(f"{Fore.YELLOW}[警告] 播放蜂鸣声失败: {e}{Style.RESET_ALL}")
            # 备用方案：使用系统默认提示音
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except:
                pass
