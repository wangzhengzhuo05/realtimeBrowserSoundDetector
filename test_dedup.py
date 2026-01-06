# -*- coding: utf-8 -*-
"""
STT 记录器去重功能测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from stt_recorder import STTRecorder
import time

def test_deduplication():
    """测试去重功能"""
    print("=" * 60)
    print("STT 记录器去重功能测试")
    print("=" * 60)
    
    # 创建测试记录器（使用较高的阈值）
    recorder = STTRecorder(save_dir="test_stt_records", dedup_threshold=0.6)
    
    # 开始会话
    session_id = recorder.start_session()
    print(f"\n✓ 会话已创建: {session_id}\n")
    
    # 模拟实时语音识别的递进式输出
    test_texts = [
        "今天我们",
        "今天我们要讲",
        "今天我们要讲解一下",
        "今天我们要讲解一下数据结构",
        "今天我们要讲解一下数据结构的基本概念",  # 这些应该被合并为一条
        "请大家打开课本",
        "请大家打开课本第五页",  # 这个应该更新上一条
        "然后我们开始",  # 这个是新内容，应该新增
        "然后我们开始今天的课程",  # 这个应该更新上一条
    ]
    
    print("模拟实时识别输出（递进式）：\n")
    for i, text in enumerate(test_texts, 1):
        print(f"{i}. 输入: {text}")
        recorder.record_text(text)
        time.sleep(0.2)  # 模拟时间间隔
    
    # 结束会话
    saved_file = recorder.end_session()
    
    print(f"\n✓ 会话已保存: {saved_file}\n")
    
    # 获取会话数据用于统计
    session_data = recorder.get_session_detail(session_id)
    
    # 读取并显示结果
    print("=" * 60)
    print("记录结果（已去重）：")
    print("=" * 60)
    
    if saved_file and os.path.exists(saved_file.replace('.json', '.txt')):
        text_file = saved_file.replace('.json', '.txt')
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
    
    print("=" * 60)
    print(f"统计信息:")
    print(f"- 输入条数: {len(test_texts)}")
    print(f"- 实际记录: {len(session_data['texts']) if session_data else 0} 条")
    print(f"- 去重率: {(1 - len(session_data['texts'])/len(test_texts))*100:.1f}%" if session_data and session_data['texts'] else "N/A")
    print("=" * 60)
    
    # 清理测试文件
    cleanup = input("\n是否删除测试文件？(y/n): ").lower().strip()
    if cleanup == 'y':
        import shutil
        if os.path.exists("test_stt_records"):
            shutil.rmtree("test_stt_records")
            print("✓ 测试文件已删除")

if __name__ == "__main__":
    test_deduplication()
