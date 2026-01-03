# -*- coding: utf-8 -*-
"""
================================================================================
配置文件 - Configuration
================================================================================

API Key 获取方式 (阿里云 DashScope):
    1. 访问阿里云官网: https://dashscope.console.aliyun.com/
    2. 注册/登录账号
    3. 开通 DashScope 服务（有免费额度）
    4. 在控制台 -> API-KEY 管理 中创建 API Key
    5. 将 API Key 填入下方 DASHSCOPE_API_KEY 变量
"""

# ==================== ASR 模式配置 ====================

# ASR 模式切换: True = 使用阿里云 DashScope API, False = 使用本地 FunASR
USE_CLOUD_API = True

# 阿里云 DashScope API Key (模式 A 需要)
# 从环境变量读取，避免将密钥写入仓库
import os
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")


# ==================== WebSocket 服务器配置 ====================

# WebSocket 服务器监听地址和端口
WS_HOST = "localhost"
WS_PORT = 8765


# ==================== 音频参数 ====================

# 采样率 (与浏览器插件保持一致)
SAMPLE_RATE = 16000


# ==================== 关键词报警配置 ====================

# 关键词列表 - 检测到这些词时触发报警
ALERT_KEYWORDS = ["签到", "点名", "打开手机", "扫码", "考勤", "输入码", "钉钉", "上课"]

# 报警冷却时间（秒）- 避免短时间内重复报警
ALERT_COOLDOWN = 5

# 自定义报警音频文件路径 (支持 .wav 格式)
# 留空或设为 None 则使用默认蜂鸣声
# 示例: CUSTOM_ALERT_SOUND = "D:/sounds/alert.wav"
CUSTOM_ALERT_SOUND = None
