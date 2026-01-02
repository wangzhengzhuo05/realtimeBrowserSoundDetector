# -*- coding: utf-8 -*-
"""
关键词检测与报警模块
检测识别文本中的关键词并触发报警
"""

import time
import threading
import winsound
import os
from typing import List

from colorama import Fore, Style


class KeywordAlert:
    """
    关键词检测与报警模块
    检测识别文本中的关键词并触发报警
    """
    
    def __init__(self, keywords: List[str], cooldown: int = 10, custom_sound: str = None):
        """
        :param keywords: 关键词列表
        :param cooldown: 报警冷却时间（秒）
        :param custom_sound: 自定义报警音频文件路径（.wav格式），为None则使用默认蜂鸣声
        """
        self.keywords = keywords
        self.cooldown = cooldown
        self.custom_sound = custom_sound
        self.last_alert_time = 0
        self.lock = threading.Lock()
        
        # 验证自定义音频文件
        if self.custom_sound:
            if os.path.exists(self.custom_sound):
                print(f"{Fore.GREEN}[信息] 已加载自定义报警音频: {self.custom_sound}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[警告] 自定义音频文件不存在: {self.custom_sound}，将使用默认蜂鸣声{Style.RESET_ALL}")
                self.custom_sound = None
        
    def check_and_alert(self, text: str) -> bool:
        """
        检查文本中是否包含关键词，如果包含则触发报警
        :param text: 识别的文本
        :return: 是否触发了报警
        """
        if not text:
            return False
        
        # 检查是否包含关键词
        detected_keywords = []
        for keyword in self.keywords:
            if keyword in text:
                detected_keywords.append(keyword)
        
        if not detected_keywords:
            return False
        
        # 检查冷却时间
        with self.lock:
            current_time = time.time()
            if current_time - self.last_alert_time < self.cooldown:
                remaining = self.cooldown - (current_time - self.last_alert_time)
                print(f"{Fore.YELLOW}[冷却中] 检测到关键词但在冷却期内，剩余 {remaining:.1f} 秒{Style.RESET_ALL}")
                return False
            
            self.last_alert_time = current_time
        
        # 触发报警
        self._trigger_alert(detected_keywords, text)
        return True
    
    def _trigger_alert(self, keywords: List[str], text: str):
        """触发报警"""
        # 控制台红色高亮警告
        print(f"\n{Fore.RED}{'!'*60}")
        print(f"{'!'*20} 检测到关键词报警 {'!'*20}")
        print(f"{'!'*60}")
        print(f"\n  关键词: {', '.join(keywords)}")
        print(f"  原文: {text}")
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
            # 播放自定义 WAV 文件（同步播放，确保完整播放）
            winsound.PlaySound(self.custom_sound, winsound.SND_FILENAME)
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
