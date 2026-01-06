"""
测试 STT 记录器的实时记录功能
模拟真实场景：启动会话 -> 记录文本 -> 查看文本 -> 结束会话
"""
import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from stt_recorder import STTRecorder
from colorama import Fore, Style, init

init(autoreset=True)

def test_live_recording():
    """测试实时记录"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}STT 实时记录测试{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # 创建记录器
    recorder = STTRecorder(save_dir="stt_records", dedup_threshold=0.6)
    
    # 启动会话
    print(f"{Fore.YELLOW}1. 启动新会话...{Style.RESET_ALL}")
    session_id = recorder.start_session()
    print(f"{Fore.GREEN}   会话ID: {session_id}{Style.RESET_ALL}\n")
    
    # 模拟实时记录
    print(f"{Fore.YELLOW}2. 模拟实时 ASR 识别...{Style.RESET_ALL}")
    
    test_texts = [
        "今天天气",
        "今天天气很好",
        "今天天气很好，我们去",
        "今天天气很好，我们去公园",
        "今天天气很好，我们去公园玩",
        "大家好",
        "大家好，欢迎",
        "大家好，欢迎来到",
        "大家好，欢迎来到直播间",
    ]
    
    for i, text in enumerate(test_texts, 1):
        recorder.record_text(text)
        time.sleep(0.3)  # 模拟 ASR 延迟
    
    print(f"\n{Fore.YELLOW}3. 检查实时文本内容...{Style.RESET_ALL}")
    current_text = recorder.get_current_text_content()
    if current_text:
        print(f"{Fore.GREEN}实时文本文件内容：{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{current_text}{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.RED}错误：无法获取实时文本！{Style.RESET_ALL}\n")
    
    # 检查 JSON 数据
    print(f"{Fore.YELLOW}4. 检查内存中的数据...{Style.RESET_ALL}")
    if recorder.current_session_data:
        texts_count = len(recorder.current_session_data["texts"])
        total_chars = recorder.current_session_data["total_chars"]
        print(f"{Fore.GREEN}   记录条数: {texts_count}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   总字符数: {total_chars}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   记录内容:{Style.RESET_ALL}")
        for entry in recorder.current_session_data["texts"]:
            print(f"   - {entry['text']}")
    print()
    
    # 结束会话
    print(f"{Fore.YELLOW}5. 结束会话...{Style.RESET_ALL}")
    saved_session_id = recorder.end_session()
    print(f"{Fore.GREEN}   会话已保存: {saved_session_id}{Style.RESET_ALL}\n")
    
    # 检查历史记录
    print(f"{Fore.YELLOW}6. 读取历史记录...{Style.RESET_ALL}")
    sessions = recorder.get_all_sessions()
    print(f"{Fore.GREEN}   历史会话数: {len(sessions)}{Style.RESET_ALL}")
    if sessions:
        last_session = sessions[-1]
        print(f"{Fore.GREEN}   最新会话: {last_session['session_id']}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   文本条数: {last_session['text_count']}{Style.RESET_ALL}")
        
        # 读取会话文本
        session_text = recorder.get_session_text_content(last_session['session_id'])
        if session_text:
            print(f"{Fore.GREEN}   会话文本：{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{session_text}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}测试完成！{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

if __name__ == "__main__":
    test_live_recording()
