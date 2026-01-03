# -*- coding: utf-8 -*-
"""
签到码记录模块
检测并保存可能的签到码（4位及以上连续数字）
"""

import re
import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
from colorama import Fore, Style


class CodeRecorder:
    """
    签到码记录器
    检测识别文本中的连续数字（4位及以上）并保存
    """
    
    def __init__(self, save_path: str = "detected_codes.json", min_digits: int = 4):
        """
        :param save_path: 保存文件路径
        :param min_digits: 最小数字位数（默认4位）
        """
        self.save_path = save_path
        self.min_digits = min_digits
        self.lock = threading.Lock()
        self.detected_codes: List[Dict] = []
        self._callback: Optional[Callable[[str, str], None]] = None
        
        # 匹配连续数字的正则（支持中文数字混合情况）
        # 匹配至少 min_digits 位连续数字
        self.pattern = re.compile(r'\d{' + str(min_digits) + r',}')
        
        # 加载已有记录
        self._load_records()
        
    def _load_records(self):
        """加载已有的签到码记录"""
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    self.detected_codes = json.load(f)
                print(f"{Fore.GREEN}[签到码] 已加载 {len(self.detected_codes)} 条历史记录{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}[签到码] 加载历史记录失败: {e}{Style.RESET_ALL}")
                self.detected_codes = []
    
    def _save_records(self):
        """保存签到码记录到文件"""
        try:
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(self.detected_codes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Fore.RED}[签到码] 保存记录失败: {e}{Style.RESET_ALL}")
    
    def set_callback(self, callback: Callable[[str, str], None]):
        """
        设置检测到签到码时的回调
        :param callback: 回调函数 (code, timestamp) -> None
        """
        self._callback = callback
    
    def check_text(self, text: str) -> List[str]:
        """
        检查文本中是否包含可能的签到码
        :param text: 识别的文本
        :return: 检测到的签到码列表
        """
        if not text:
            return []
        
        # 查找所有连续数字
        matches = self.pattern.findall(text)
        
        new_codes = []
        now = datetime.now()
        for code in matches:
            # 查找最近一次记录的时间，超过 5 分钟则允许重复记录
            last_record = next((r for r in reversed(self.detected_codes) if r.get("code") == code), None)
            if last_record:
                try:
                    last_time = datetime.strptime(last_record.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
                    delta = (now - last_time).total_seconds()
                    if delta < 300:  # 5 分钟内重复出现则跳过
                        print(f"{Fore.YELLOW}[签到码] 检测到重复签到码 {code}，距离上次仅 {int(delta)} 秒，跳过记录{Style.RESET_ALL}")
                        continue
                except Exception:
                    # 时间解析异常时，直接继续记录以免漏掉
                    pass
            
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            record = {
                "code": code,
                "timestamp": timestamp,
                "context": text[:100]  # 保存上下文（最多100字符）
            }
            
            with self.lock:
                self.detected_codes.append(record)
                self._save_records()
            
            new_codes.append(code)
            print(f"{Fore.CYAN}[签到码] 检测到可能的签到码: {code} (时间: {timestamp}){Style.RESET_ALL}")
            
            # 触发回调
            if self._callback:
                self._callback(code, timestamp)
        
        return new_codes
    
    def get_recent_codes(self, count: int = 10) -> List[Dict]:
        """
        获取最近的签到码记录
        :param count: 获取数量
        :return: 签到码记录列表
        """
        with self.lock:
            return self.detected_codes[-count:]
    
    def clear_records(self):
        """清空所有记录"""
        with self.lock:
            self.detected_codes = []
            self._save_records()
        print(f"{Fore.YELLOW}[签到码] 已清空所有记录{Style.RESET_ALL}")
