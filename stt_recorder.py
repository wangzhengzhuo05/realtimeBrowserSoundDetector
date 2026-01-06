# -*- coding: utf-8 -*-
"""
STT 内容记录器
记录每次监听会话的语音识别内容，支持查看历史记录
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from colorama import Fore, Style


class STTRecorder:
    """
    STT 内容记录器
    负责记录每次监听会话的语音识别内容并保存到本地
    """
    
    def __init__(self, save_dir: str = "stt_records", dedup_threshold: float = 0.6):
        """
        初始化 STT 记录器
        
        Args:
            save_dir: 记录文件保存目录
            dedup_threshold: 去重相似度阈值（0-1），默认0.6。值越大去重越严格
        """
        self.save_dir = save_dir
        self.dedup_threshold = dedup_threshold  # 去重阈值
        self.current_session_id = None
        self.current_session_data = None
        self.session_start_time = None
        self.current_text_file = None  # 当前会话的文本文件句柄
        self.current_text_file_path = None  # 当前文本文件路径
        self.last_recorded_text = ""  # 上一条记录的文本（用于去重）
        self.last_file_position = 0  # 上一条记录在文件中的位置
        
        # 确保保存目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        # 会话索引文件
        self.index_file = os.path.join(save_dir, "index.json")
        self.sessions_index = self._load_index()
        
    def _load_index(self) -> List[Dict]:
        """加载会话索引"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"{Fore.RED}[错误] 加载会话索引失败: {e}{Style.RESET_ALL}")
                return []
        return []
    
    def _save_index(self):
        """保存会话索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Fore.RED}[错误] 保存会话索引失败: {e}{Style.RESET_ALL}")
    
    def start_session(self) -> str:
        """
        开始一个新的监听会话
        
        Returns:
            session_id: 会话ID
        """
        self.session_start_time = datetime.now()
        self.current_session_id = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        
        self.current_session_data = {
            "session_id": self.current_session_id,
            "start_time": self.session_start_time.isoformat(),
            "end_time": None,
            "duration": 0,
            "texts": [],  # 识别的文本列表
            "total_chars": 0,  # 总字符数
            "keywords_detected": []  # 检测到的关键词
        }
        
        # 创建实时文本文件
        self.current_text_file_path = os.path.join(self.save_dir, f"{self.current_session_id}.txt")
        try:
            self.current_text_file = open(self.current_text_file_path, 'w', encoding='utf-8')
            # 写入会话头信息
            self.current_text_file.write(f"====================================\n")
            self.current_text_file.write(f"STT 记录会话\n")
            self.current_text_file.write(f"会话ID: {self.current_session_id}\n")
            self.current_text_file.write(f"开始时间: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.current_text_file.write(f"====================================\n\n")
            self.current_text_file.flush()
        except Exception as e:
            print(f"{Fore.RED}[错误] 创建文本文件失败: {e}{Style.RESET_ALL}")
        
        # 重置去重状态
        self.last_recorded_text = ""
        self.last_file_position = 0
        
        print(f"{Fore.GREEN}[STT记录] 开始新会话: {self.current_session_id}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[STT记录] 文本文件: {self.current_text_file_path}{Style.RESET_ALL}")
        return self.current_session_id
    
    def _is_duplicate_or_extension(self, new_text: str, old_text: str, threshold: float = 0.6) -> bool:
        """
        判断新文本是否是旧文本的重复或延伸
        
        Args:
            new_text: 新识别的文本
            old_text: 上一条文本
            threshold: 相似度阈值（0-1），默认0.6
            
        Returns:
            True表示是重复/延伸，应该替换；False表示是新内容，应该追加
        """
        if not old_text:
            return False
        
        new_text = new_text.strip()
        old_text = old_text.strip()
        
        # 完全相同
        if new_text == old_text:
            return True
        
        # 策略1: 新文本包含旧文本（延伸）
        # 例如: "今天我们" -> "今天我们要讲"
        if old_text in new_text:
            # 旧文本占新文本的比例
            ratio = len(old_text) / len(new_text)
            # 对于短文本降低阈值要求
            min_len = min(len(old_text), len(new_text))
            effective_threshold = threshold if min_len > 10 else threshold * 0.8
            if ratio >= effective_threshold:
                return True
        
        # 策略2: 旧文本包含新文本（重复或缩短）
        if new_text in old_text:
            ratio = len(new_text) / len(old_text)
            min_len = min(len(old_text), len(new_text))
            effective_threshold = threshold if min_len > 10 else threshold * 0.8
            if ratio >= effective_threshold:
                return True
        
        # 策略3: 计算最长公共子串（处理部分重叠）
        common_length = self._longest_common_substring_length(new_text, old_text)
        min_length = min(len(new_text), len(old_text))
        
        if min_length > 0:
            similarity = common_length / min_length
            # 对于短文本降低阈值
            effective_threshold = threshold if min_length > 10 else threshold * 0.8
            if similarity >= effective_threshold:
                return True
        
        return False
    
    def _longest_common_substring_length(self, s1: str, s2: str) -> int:
        """计算两个字符串的最长公共子串长度"""
        m, n = len(s1), len(s2)
        if m == 0 or n == 0:
            return 0
        
        # 动态规划
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        max_length = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    max_length = max(max_length, dp[i][j])
        
        return max_length
    
    def record_text(self, text: str, timestamp: Optional[str] = None):
        """
        记录识别的文本（带智能去重）
        
        Args:
            text: 识别的文本
            timestamp: 时间戳（可选，默认使用当前时间）
        """
        if not self.current_session_id:
            print(f"{Fore.YELLOW}[STT记录] 检测到无会话，自动启动新会话{Style.RESET_ALL}")
            self.start_session()
        
        if not text or not text.strip():
            return
        
        text = text.strip()
        now = datetime.now()
        if timestamp is None:
            timestamp = now.isoformat()
        
        # 检查是否与上一条重复（使用配置的阈值）
        is_duplicate = self._is_duplicate_or_extension(text, self.last_recorded_text, self.dedup_threshold)
        
        if is_duplicate and self.current_session_data["texts"]:
            # 更新最后一条记录（替换而不是追加）
            last_entry = self.current_session_data["texts"][-1]
            char_diff = len(text) - last_entry["char_count"]
            
            print(f"{Fore.CYAN}[STT记录] 更新重复/延伸文本 ({len(text)}字){Style.RESET_ALL}")
            
            last_entry["text"] = text
            last_entry["char_count"] = len(text)
            last_entry["timestamp"] = timestamp
            self.current_session_data["total_chars"] += char_diff
            
            # 更新文本文件（回退并重写最后一行）
            if self.current_text_file:
                try:
                    # 定位到上一条记录的位置
                    self.current_text_file.seek(self.last_file_position)
                    # 覆盖写入新内容
                    time_str = now.strftime('%H:%M:%S')
                    line = f"[{time_str}] {text}\n"
                    self.current_text_file.write(line)
                    # 截断文件（删除后面的旧内容）
                    self.current_text_file.truncate()
                    self.current_text_file.flush()
                    # 更新位置
                    self.last_file_position = self.current_text_file.tell()
                except Exception as e:
                    print(f"{Fore.YELLOW}[警告] 更新文本文件失败: {e}{Style.RESET_ALL}")
        else:
            # 添加新记录
            print(f"{Fore.GREEN}[STT记录] 记录新文本 ({len(text)}字): {text[:30]}...{Style.RESET_ALL}" if len(text) > 30 else f"{Fore.GREEN}[STT记录] 记录新文本 ({len(text)}字): {text}{Style.RESET_ALL}")
            
            text_entry = {
                "timestamp": timestamp,
                "text": text,
                "char_count": len(text)
            }
            
            self.current_session_data["texts"].append(text_entry)
            self.current_session_data["total_chars"] += text_entry["char_count"]
            
            # 写入文本文件
            if self.current_text_file:
                try:
                    # 记录当前位置
                    self.last_file_position = self.current_text_file.tell()
                    time_str = now.strftime('%H:%M:%S')
                    self.current_text_file.write(f"[{time_str}] {text}\n")
                    self.current_text_file.flush()
                except Exception as e:
                    print(f"{Fore.RED}[错误] 写入文本文件失败: {e}{Style.RESET_ALL}")
        
        # 更新最后记录的文本
        self.last_recorded_text = text
    
    def record_keyword_detected(self, keyword: str, matched_text: str):
        """
        记录检测到的关键词
        
        Args:
            keyword: 检测到的关键词
            matched_text: 匹配的文本片段
        """
        if not self.current_session_id:
            return
        
        keyword_entry = {
            "timestamp": datetime.now().isoformat(),
            "keyword": keyword,
            "matched_text": matched_text
        }
        
        self.current_session_data["keywords_detected"].append(keyword_entry)
    
    def end_session(self) -> Optional[str]:
        """
        结束当前会话并保存
        
        Returns:
            保存的文件路径，如果没有活动会话则返回 None
        """
        if not self.current_session_id:
            return None
        
        end_time = datetime.now()
        self.current_session_data["end_time"] = end_time.isoformat()
        
        # 关闭文本文件
        if self.current_text_file:
            try:
                self.current_text_file.close()
                self.current_text_file = None
            except Exception as e:
                print(f"{Fore.RED}[错误] 关闭文本文件失败: {e}{Style.RESET_ALL}")
        
        # 计算会话时长（秒）
        duration = (end_time - self.session_start_time).total_seconds()
        self.current_session_data["duration"] = round(duration, 2)
        
        # 重新生成文本文件（确保与JSON一致，去除中间重复状态）
        try:
            with open(self.current_text_file_path, 'w', encoding='utf-8') as f:
                f.write(f"====================================\n")
                f.write(f"STT 记录会话\n")
                f.write(f"会话ID: {self.current_session_id}\n")
                f.write(f"开始时间: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"====================================\n\n")
                
                # 写入所有文本记录
                for text_entry in self.current_session_data["texts"]:
                    timestamp = datetime.fromisoformat(text_entry["timestamp"])
                    time_str = timestamp.strftime('%H:%M:%S')
                    f.write(f"[{time_str}] {text_entry['text']}\n")
                
                f.write(f"\n====================================\n")
                f.write(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"====================================\n")
        except Exception as e:
            print(f"{Fore.RED}[错误] 重新生成文本文件失败: {e}{Style.RESET_ALL}")
        
        # 保存会话数据到文件
        session_file = os.path.join(self.save_dir, f"{self.current_session_id}.json")
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_session_data, f, ensure_ascii=False, indent=2)
            
            # 更新索引
            index_entry = {
                "session_id": self.current_session_id,
                "start_time": self.current_session_data["start_time"],
                "end_time": self.current_session_data["end_time"],
                "duration": self.current_session_data["duration"],
                "total_chars": self.current_session_data["total_chars"],
                "text_count": len(self.current_session_data["texts"]),
                "keywords_count": len(self.current_session_data["keywords_detected"]),
                "file_path": session_file
            }
            
            # 添加到索引（最新的在前面）
            self.sessions_index.insert(0, index_entry)
            self._save_index()
            
            print(f"{Fore.GREEN}[STT记录] 会话已保存: {session_file}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[统计] 时长: {duration:.1f}秒, 文本数: {len(self.current_session_data['texts'])}, 字符数: {self.current_session_data['total_chars']}{Style.RESET_ALL}")
            
            # 重置当前会话
            self.current_session_id = None
            self.current_session_data = None
            self.session_start_time = None
            
            return session_file
            
        except Exception as e:
            print(f"{Fore.RED}[错误] 保存会话记录失败: {e}{Style.RESET_ALL}")
            return None
    
    def get_all_sessions(self) -> List[Dict]:
        """
        获取所有会话的索引信息
        
        Returns:
            会话索引列表（按时间倒序）
        """
        return self.sessions_index
    
    def get_session_detail(self, session_id: str) -> Optional[Dict]:
        """
        获取指定会话的详细内容
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话详细数据，如果不存在则返回 None
        """
        session_file = os.path.join(self.save_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"{Fore.RED}[错误] 读取会话记录失败: {e}{Style.RESET_ALL}")
                return None
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除指定的会话记录
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否删除成功
        """
        session_file = os.path.join(self.save_dir, f"{session_id}.json")
        
        try:
            # 从索引中移除
            self.sessions_index = [s for s in self.sessions_index if s["session_id"] != session_id]
            self._save_index()
            
            # 删除文件
            if os.path.exists(session_file):
                os.remove(session_file)
            
            print(f"{Fore.GREEN}[STT记录] 已删除会话: {session_id}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[错误] 删除会话记录失败: {e}{Style.RESET_ALL}")
            return False
    
    def export_session_to_text(self, session_id: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        将会话记录导出为纯文本文件
        
        Args:
            session_id: 会话ID
            output_file: 输出文件路径（可选）
            
        Returns:
            导出文件路径，失败返回 None
        """
        session_data = self.get_session_detail(session_id)
        if not session_data:
            return None
        
        if output_file is None:
            output_file = os.path.join(self.save_dir, f"{session_id}.txt")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # 写入会话信息
                f.write(f"会话ID: {session_data['session_id']}\n")
                f.write(f"开始时间: {session_data['start_time']}\n")
                f.write(f"结束时间: {session_data['end_time']}\n")
                f.write(f"持续时长: {session_data['duration']} 秒\n")
                f.write(f"总字符数: {session_data['total_chars']}\n")
                f.write("=" * 60 + "\n\n")
                
                # 写入识别的文本
                f.write("识别内容:\n")
                f.write("-" * 60 + "\n")
                for text_entry in session_data['texts']:
                    f.write(f"[{text_entry['timestamp']}] {text_entry['text']}\n")
                
                # 写入关键词检测记录
                if session_data['keywords_detected']:
                    f.write("\n" + "=" * 60 + "\n")
                    f.write("关键词检测记录:\n")
                    f.write("-" * 60 + "\n")
                    for kw_entry in session_data['keywords_detected']:
                        f.write(f"[{kw_entry['timestamp']}] 关键词: {kw_entry['keyword']}\n")
                        f.write(f"  匹配文本: {kw_entry['matched_text']}\n\n")
            
            print(f"{Fore.GREEN}[STT记录] 已导出为文本: {output_file}{Style.RESET_ALL}")
            return output_file
            
        except Exception as e:
            print(f"{Fore.RED}[错误] 导出文本失败: {e}{Style.RESET_ALL}")
            return None
    
    def get_current_session_id(self) -> Optional[str]:
        """获取当前活动会话的ID"""
        return self.current_session_id
    
    def is_recording(self) -> bool:
        """检查是否正在记录"""
        return self.current_session_id is not None
    
    def get_current_text_content(self) -> Optional[str]:
        """获取当前会话的文本文件内容"""
        if self.current_text_file_path and os.path.exists(self.current_text_file_path):
            try:
                with open(self.current_text_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"{Fore.RED}[错误] 读取当前文本文件失败: {e}{Style.RESET_ALL}")
                return None
        return None
    
    def get_session_text_content(self, session_id: str) -> Optional[str]:
        """获取指定会话的文本文件内容"""
        text_file = os.path.join(self.save_dir, f"{session_id}.txt")
        if os.path.exists(text_file):
            try:
                with open(text_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"{Fore.RED}[错误] 读取文本文件失败: {e}{Style.RESET_ALL}")
                return None
        return None
