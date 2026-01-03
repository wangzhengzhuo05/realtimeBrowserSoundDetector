# -*- coding: utf-8 -*-
"""
动态配置管理模块
支持从 JSON 文件加载和保存配置
"""

import json
import os
from pathlib import Path
from typing import List, Optional

# 配置文件路径
CONFIG_FILE = Path(__file__).parent / "config.json"
# 本地敏感配置（不会提交到 git）
LOCAL_SECRETS_FILE = Path(__file__).parent / ".secrets.json"

# 默认配置
DEFAULT_CONFIG = {
    "use_cloud_api": True,
    "api_key": "",
    "ws_host": "localhost",
    "ws_port": 8765,
    "keywords": ["签到", "点名", "打开手机", "扫码", "考勤", "输入码", "钉钉", "上课"],
    "cooldown": 5,
    "custom_sound": None,
    "web_host": "localhost",
    "web_port": 8080,
    "enable_semantic": False,
    "semantic_threshold": 0.65,
    "semantic_model": "text-embedding-v3",
    "detect_mode": "asr",
    "debug_mode": False,
    "mute_playback": False,
    "llm_detect_interval": 3.0,
    "llm_model": "qwen-turbo"
}


class ConfigManager:
    """
    配置管理器
    支持从 JSON 文件动态加载配置
    """
    
    def __init__(self):
        self._config = None
        self._load()
    
    def _load(self):
        """加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                # 合并默认值（处理新增的配置项）
                for key, value in DEFAULT_CONFIG.items():
                    if key not in self._config:
                        self._config[key] = value
                # 叠加本地敏感配置（仅本机，不入库）
                self._load_local_secrets()
            except Exception as e:
                print(f"[警告] 加载配置文件失败: {e}，使用默认配置")
                self._config = DEFAULT_CONFIG.copy()
        else:
            # 尝试从旧的 config.py 迁移
            self._migrate_from_py()

    def _load_local_secrets(self):
        """从本地敏感配置文件加载密钥（不会被 git 追踪）"""
        if not LOCAL_SECRETS_FILE.exists():
            return
        try:
            with open(LOCAL_SECRETS_FILE, "r", encoding="utf-8") as f:
                secrets_data = json.load(f)
            # 仅允许覆盖敏感字段
            if isinstance(secrets_data, dict):
                if secrets_data.get("api_key"):
                    self._config["api_key"] = secrets_data["api_key"]
        except Exception as e:
            print(f"[警告] 加载本地敏感配置失败: {e}")
    
    def _migrate_from_py(self):
        """从 config.py 迁移配置"""
        try:
            # 动态导入避免循环依赖
            import importlib.util
            spec = importlib.util.spec_from_file_location("old_config", Path(__file__).parent / "config.py")
            if spec and spec.loader:
                old_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(old_config)
                
                self._config = {
                    "use_cloud_api": getattr(old_config, "USE_CLOUD_API", True),
                    "api_key": getattr(old_config, "DASHSCOPE_API_KEY", ""),
                    "ws_host": getattr(old_config, "WS_HOST", "localhost"),
                    "ws_port": getattr(old_config, "WS_PORT", 8765),
                    "keywords": getattr(old_config, "ALERT_KEYWORDS", DEFAULT_CONFIG["keywords"]),
                    "cooldown": getattr(old_config, "ALERT_COOLDOWN", 5),
                    "custom_sound": getattr(old_config, "CUSTOM_ALERT_SOUND", None),
                    "web_host": "localhost",
                    "web_port": 8080
                }
                # 保存到 JSON
                self.save()
                print("[信息] 已从 config.py 迁移配置到 config.json")
                return
        except Exception as e:
            print(f"[警告] 迁移配置失败: {e}")
        
        # 使用默认配置
        self._config = DEFAULT_CONFIG.copy()
        self.save()
    
    def save(self):
        """保存配置到文件"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
    
    def reload(self):
        """重新加载配置"""
        self._load()
    
    @property
    def use_cloud_api(self) -> bool:
        return self._config.get("use_cloud_api", True)
    
    @property
    def api_key(self) -> str:
        return self._config.get("api_key", "") or os.getenv("DASHSCOPE_API_KEY", "")
    
    @property
    def ws_host(self) -> str:
        return self._config.get("ws_host", "localhost")
    
    @property
    def ws_port(self) -> int:
        return self._config.get("ws_port", 8765)
    
    @property
    def keywords(self) -> List[str]:
        return self._config.get("keywords", [])
    
    @property
    def cooldown(self) -> int:
        return self._config.get("cooldown", 5)
    
    @property
    def custom_sound(self) -> Optional[str]:
        return self._config.get("custom_sound")
    
    @property
    def web_host(self) -> str:
        return self._config.get("web_host", "localhost")
    
    @property
    def web_port(self) -> int:
        return self._config.get("web_port", 8080)
    
    @property
    def enable_semantic(self) -> bool:
        return self._config.get("enable_semantic", False)
    
    @property
    def semantic_threshold(self) -> float:
        return self._config.get("semantic_threshold", 0.65)

    @property
    def semantic_model(self) -> str:
        return self._config.get("semantic_model", "text-embedding-v3")
    
    @property
    def detect_mode(self) -> str:
        """检测模式: asr, asr+llm, qwen2-audio"""
        return self._config.get("detect_mode", "asr")
    
    @property
    def debug_mode(self) -> bool:
        """Debug模式：同时运行 ASR 和 Qwen2-Audio 进行对比"""
        return self._config.get("debug_mode", False)
    
    @property
    def mute_playback(self) -> bool:
        """静音外放：捕获音频后不通过扬声器播放"""
        return self._config.get("mute_playback", False)
    
    @property
    def llm_detect_interval(self) -> float:
        """LLM 检测间隔（秒）"""
        return self._config.get("llm_detect_interval", 3.0)
    
    @property
    def llm_model(self) -> str:
        """LLM 模型名称"""
        return self._config.get("llm_model", "qwen-turbo")
    
    def to_dict(self) -> dict:
        """返回配置字典"""
        return self._config.copy()
    
    def update(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if key in self._config:
                self._config[key] = value
        self.save()


# 全局配置实例
config = ConfigManager()
