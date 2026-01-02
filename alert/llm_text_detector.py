# -*- coding: utf-8 -*-
"""
LLM 文本语义检测模块
使用大模型对 ASR 转写的文本进行语义理解
检测是否有签到、点名等意图
"""

import time
import threading
from typing import List, Callable, Optional
from colorama import Fore, Style

try:
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    print(f"{Fore.YELLOW}[警告] dashscope 未安装，LLM 文本检测不可用{Style.RESET_ALL}")


class LLMTextDetector:
    """
    LLM 文本语义检测器
    每隔固定间隔将累积的 ASR 文本发送给大模型进行语义分析
    """
    
    def __init__(self, api_key: str, keywords: List[str], 
                 interval: float = 3.0, cooldown: int = 10,
                 model: str = "qwen-turbo"):
        """
        :param api_key: DashScope API Key
        :param keywords: 需要检测的关键词/意图列表
        :param interval: 检测间隔（秒）
        :param cooldown: 报警冷却时间（秒）
        :param model: 使用的 LLM 模型
        """
        self.api_key = api_key
        self.keywords = keywords
        self.interval = interval
        self.cooldown = cooldown
        self.model = model
        
        self._text_buffer = ""
        self._buffer_lock = threading.Lock()
        self._last_alert_time = 0
        
        self._running = False
        self._detect_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self._alert_callback: Optional[Callable[[List[str], str], None]] = None
        self._analysis_callback: Optional[Callable[[str], None]] = None
        
        # 构建系统提示词
        keywords_str = "、".join(keywords)
        self._system_prompt = f"""你是一个课堂语义检测助手。你的任务是分析学生课堂上听到的语音转写文本，判断老师是否在进行以下操作：{keywords_str}。

请注意：
1. 文本可能有识别错误，需要根据上下文理解真实意图
2. "签到"的变体可能包括：签个到、点个名、打卡、扫码签到、考勤等
3. 只关注是否有明确的签到/点名意图，忽略其他无关内容

请用 JSON 格式回复，包含两个字段：
- detected: 布尔值，是否检测到相关意图
- keywords: 数组，检测到的关键词/意图列表（如果 detected 为 false 则为空数组）
- reason: 简短说明检测理由

只输出 JSON，不要输出其他内容。"""
    
    def set_alert_callback(self, callback: Callable[[List[str], str], None]):
        """设置报警回调函数"""
        self._alert_callback = callback
    
    def set_analysis_callback(self, callback: Callable[[str], None]):
        """设置分析结果回调函数（用于显示 LLM 的分析结果）"""
        self._analysis_callback = callback
    
    def feed_text(self, text: str):
        """喂入 ASR 识别的文本"""
        if text:
            with self._buffer_lock:
                self._text_buffer += text
    
    def start(self):
        """启动检测线程"""
        if not DASHSCOPE_AVAILABLE:
            print(f"{Fore.RED}[错误] dashscope 未安装，无法启动 LLM 检测{Style.RESET_ALL}")
            return
        
        self._running = True
        self._detect_thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._detect_thread.start()
        print(f"{Fore.CYAN}[信息] LLM 文本检测器已启动 (间隔: {self.interval}秒){Style.RESET_ALL}")
    
    def stop(self):
        """停止检测线程"""
        self._running = False
        if self._detect_thread:
            self._detect_thread.join(timeout=2)
    
    def _detect_loop(self):
        """检测循环"""
        while self._running:
            time.sleep(self.interval)
            
            # 获取并清空缓冲区
            with self._buffer_lock:
                text = self._text_buffer
                self._text_buffer = ""
            
            if not text or len(text.strip()) < 2:
                continue
            
            # 调用 LLM 分析
            try:
                result = self._analyze_text(text)
                if result and result.get("detected"):
                    keywords = result.get("keywords", [])
                    reason = result.get("reason", "")
                    
                    # 检查冷却时间
                    current_time = time.time()
                    if current_time - self._last_alert_time >= self.cooldown:
                        self._last_alert_time = current_time
                        
                        print(f"{Fore.GREEN}[LLM检测] 检测到意图: {', '.join(keywords)}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}[LLM检测] 原因: {reason}{Style.RESET_ALL}")
                        
                        if self._alert_callback:
                            self._alert_callback(keywords, text)
                    else:
                        print(f"{Fore.YELLOW}[LLM检测] 冷却中，跳过报警{Style.RESET_ALL}")
                else:
                    # 可选：显示未检测到的分析结果
                    if self._analysis_callback and result:
                        self._analysis_callback(f"未检测到关键意图")
                        
            except Exception as e:
                print(f"{Fore.RED}[LLM检测] 分析失败: {e}{Style.RESET_ALL}")
    
    def _analyze_text(self, text: str) -> Optional[dict]:
        """使用 LLM 分析文本"""
        try:
            response = Generation.call(
                model=self.model,
                api_key=self.api_key,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": f"请分析以下课堂语音转写文本：\n\n{text}"}
                ],
                result_format="message"
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                # 解析 JSON 响应
                import json
                # 尝试提取 JSON
                content = content.strip()
                if content.startswith("```"):
                    # 去除 markdown 代码块
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1])
                
                return json.loads(content)
            else:
                print(f"{Fore.RED}[LLM检测] API 错误: {response.message}{Style.RESET_ALL}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}[LLM检测] 调用失败: {e}{Style.RESET_ALL}")
            return None
