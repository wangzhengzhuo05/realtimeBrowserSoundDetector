# -*- coding: utf-8 -*-
"""
Web 服务器模块
提供 HTTP API 和静态文件服务
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Callable, Set

from aiohttp import web, WSMsgType

from colorama import Fore, Style


class WebServer:
    """
    Web 服务器
    提供配置管理 API 和实时状态推送
    """
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # 状态 WebSocket 客户端
        self.status_clients: Set[web.WebSocketResponse] = set()
        
        # 配置文件路径
        self.config_file = Path(__file__).parent.parent / "config.json"
        
        # 静态文件目录
        self.static_dir = Path(__file__).parent / "static"
        
        # 重启回调
        self.restart_callback: Callable = None
        
        # 配置更新回调（用于热更新运行中的组件）
        self.config_update_callback: Callable = None
        
        # 设置路由
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/api/config", self._handle_get_config)
        self.app.router.add_post("/api/config", self._handle_save_config)
        self.app.router.add_post("/api/restart", self._handle_restart)
        self.app.router.add_post("/api/validate-sound", self._handle_validate_sound)
        self.app.router.add_get("/api/list-sounds", self._handle_list_sounds)
        self.app.router.add_get("/ws/status", self._handle_status_ws)
        
        # 静态文件
        self.app.router.add_get("/", self._handle_index)
        self.app.router.add_static("/", self.static_dir, name="static")
    
    async def _handle_index(self, request: web.Request) -> web.Response:
        """返回首页"""
        index_file = self.static_dir / "index.html"
        if index_file.exists():
            return web.FileResponse(index_file)
        return web.Response(text="Index not found", status=404)
    
    async def _handle_get_config(self, request: web.Request) -> web.Response:
        """获取配置"""
        try:
            config = self._load_config()
            return web.json_response(config)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_save_config(self, request: web.Request) -> web.Response:
        """保存配置"""
        try:
            data = await request.json()
            self._save_config(data)
            
            # 通知配置更新回调（用于热更新运行中的组件）
            if self.config_update_callback:
                try:
                    self.config_update_callback(data)
                except Exception as e:
                    print(f"{Fore.YELLOW}[警告] 配置热更新失败: {e}{Style.RESET_ALL}")
            
            return web.json_response({"success": True, "message": "配置已保存"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_restart(self, request: web.Request) -> web.Response:
        """重启服务"""
        try:
            if self.restart_callback:
                # 异步执行重启
                asyncio.create_task(self._do_restart())
            return web.json_response({"success": True, "message": "服务正在重启"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_validate_sound(self, request: web.Request) -> web.Response:
        """验证音频文件路径或URL是否有效"""
        try:
            data = await request.json()
            path = data.get("path", "").strip()
            
            if not path:
                return web.json_response({"valid": False, "message": "路径为空"})
            
            # 支持的扩展名
            exts = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}
            
            # 检查是否为 URL
            if path.startswith(("http://", "https://")):
                import aiohttp
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.head(path, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            if resp.status == 200:
                                content_type = resp.headers.get("Content-Type", "")
                                if "audio" in content_type or any(path.lower().endswith(e) for e in exts):
                                    return web.json_response({"valid": True, "message": "URL 有效", "type": "url"})
                                else:
                                    return web.json_response({"valid": False, "message": f"URL 可访问但可能不是音频文件 (Content-Type: {content_type})"})
                            else:
                                return web.json_response({"valid": False, "message": f"URL 不可访问 (HTTP {resp.status})"})
                except asyncio.TimeoutError:
                    return web.json_response({"valid": False, "message": "URL 请求超时"})
                except Exception as e:
                    return web.json_response({"valid": False, "message": f"URL 请求失败: {str(e)}"})
            
            # 本地文件路径
            file_path = Path(path)
            if not file_path.is_absolute():
                # 相对路径转为绝对路径（相对于项目根目录）
                file_path = Path(__file__).parent.parent / path
            
            if not file_path.exists():
                return web.json_response({"valid": False, "message": "文件不存在"})
            
            if not file_path.is_file():
                return web.json_response({"valid": False, "message": "路径不是文件"})
            
            if file_path.suffix.lower() not in exts:
                return web.json_response({"valid": False, "message": f"不支持的格式 ({file_path.suffix})，支持: {', '.join(exts)}"})
            
            # 检查文件大小
            size_mb = file_path.stat().st_size / (1024 * 1024)
            return web.json_response({
                "valid": True, 
                "message": f"文件有效 ({size_mb:.2f} MB)",
                "type": "file",
                "size": file_path.stat().st_size
            })
            
        except Exception as e:
            return web.json_response({"valid": False, "message": f"验证失败: {str(e)}"})
    
    async def _handle_list_sounds(self, request: web.Request) -> web.Response:
        """列出可用的自定义音频文件"""
        try:
            sounds_dir = Path(__file__).parent.parent / "assets" / "custom_sounds"
            sounds = []
            
            if sounds_dir.exists():
                exts = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}
                for file in sounds_dir.iterdir():
                    if file.is_file() and file.suffix.lower() in exts:
                        # 使用相对路径，确保跨电脑兼容
                        rel_path = f"assets/custom_sounds/{file.name}"
                        size_mb = file.stat().st_size / (1024 * 1024)
                        sounds.append({
                            "name": file.name,
                            "path": rel_path,  # 使用相对路径
                            "absolute_path": str(file.absolute()).replace("\\", "/"),
                            "size": f"{size_mb:.2f} MB",
                            "format": file.suffix[1:].upper()
                        })
            
            return web.json_response({"sounds": sounds})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _do_restart(self):
        """执行重启"""
        await asyncio.sleep(0.5)  # 等待响应发送
        if self.restart_callback:
            await self.restart_callback()
    
    async def _handle_status_ws(self, request: web.Request) -> web.WebSocketResponse:
        """处理状态 WebSocket 连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.status_clients.add(ws)
        print(f"{Fore.CYAN}[Web] 状态客户端已连接 (共 {len(self.status_clients)} 个){Style.RESET_ALL}")
        
        try:
            # 发送初始状态
            await ws.send_json({
                "type": "status",
                "status": "online",
                "message": "已连接"
            })
            
            # 保持连接
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # 处理客户端消息（如果需要）
                    pass
                elif msg.type == WSMsgType.ERROR:
                    print(f"{Fore.YELLOW}[Web] WebSocket 错误: {ws.exception()}{Style.RESET_ALL}")
                    break
        finally:
            self.status_clients.discard(ws)
            print(f"{Fore.CYAN}[Web] 状态客户端已断开 (剩余 {len(self.status_clients)} 个){Style.RESET_ALL}")
        
        return ws
    
    async def broadcast_status(self, data: dict):
        """广播状态给所有客户端"""
        if not self.status_clients:
            return
        
        closed_clients = set()
        for ws in self.status_clients:
            try:
                if not ws.closed:
                    await ws.send_json(data)
                else:
                    closed_clients.add(ws)
            except Exception as e:
                closed_clients.add(ws)
        
        # 移除已关闭的客户端
        self.status_clients -= closed_clients
    
    async def send_recognition(self, text: str, source: str = None):
        """发送识别结果"""
        msg = {
            "type": "recognition",
            "text": text
        }
        if source:
            msg["source"] = source
        await self.broadcast_status(msg)
    
    async def send_alert(self, keywords: list, text: str, source: str = None):
        """发送报警通知"""
        msg = {
            "type": "alert",
            "keywords": keywords,
            "text": text
        }
        if source:
            msg["source"] = source
        await self.broadcast_status(msg)
    
    async def send_llm_status(self, detected: bool, reason: str = ""):
        """发送 LLM 检测状态"""
        await self.broadcast_status({
            "type": "llm_status",
            "detected": detected,
            "reason": reason
        })
    
    async def send_code_detected(self, code: str, timestamp: str):
        """发送签到码检测通知"""
        await self.broadcast_status({
            "type": "code_detected",
            "code": code,
            "timestamp": timestamp
        })
    
    def _load_config(self) -> dict:
        """加载配置"""
        # 如果 JSON 配置文件存在，从中加载
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 填充新增默认字段
            if "semantic_model" not in cfg:
                cfg["semantic_model"] = "text-embedding-v3"
            if "detect_mode" not in cfg:
                cfg["detect_mode"] = "asr"
            if "debug_mode" not in cfg:
                cfg["debug_mode"] = False
            if "mute_playback" not in cfg:
                cfg["mute_playback"] = False
            return cfg
        
        # 否则从 config.py 加载默认值
        try:
            import config
            return {
                "use_cloud_api": getattr(config, "USE_CLOUD_API", True),
                "api_key": getattr(config, "DASHSCOPE_API_KEY", ""),
                "ws_host": getattr(config, "WS_HOST", "localhost"),
                "ws_port": getattr(config, "WS_PORT", 8765),
                "keywords": getattr(config, "ALERT_KEYWORDS", []),
                "cooldown": getattr(config, "ALERT_COOLDOWN", 5),
                "custom_sound": getattr(config, "CUSTOM_ALERT_SOUND", None)
            }
        except ImportError:
            return {
                "use_cloud_api": True,
                "api_key": "",
                "ws_host": "localhost",
                "ws_port": 8765,
                "keywords": ["签到", "点名", "打开手机", "扫码"],
                "cooldown": 5,
                "custom_sound": None
            }
    
    def _save_config(self, data: dict):
        """保存配置到 JSON 文件"""
        config = {
            "use_cloud_api": data.get("use_cloud_api", True),
            "api_key": data.get("api_key", ""),
            "ws_host": data.get("ws_host", "localhost"),
            "ws_port": data.get("ws_port", 8765),
            "keywords": data.get("keywords", []),
            "cooldown": data.get("cooldown", 5),
            "custom_sound": data.get("custom_sound"),
            "enable_semantic": data.get("enable_semantic", False),
            "semantic_threshold": data.get("semantic_threshold", 0.65),
            "semantic_model": data.get("semantic_model", "text-embedding-v3"),
            "detect_mode": data.get("detect_mode", "asr"),
            "debug_mode": data.get("debug_mode", False),
            "mute_playback": data.get("mute_playback", False)
        }
        
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"{Fore.GREEN}[Web] 配置已保存到 {self.config_file}{Style.RESET_ALL}")
    
    def set_restart_callback(self, callback: Callable):
        """设置重启回调"""
        self.restart_callback = callback
    
    def set_config_update_callback(self, callback: Callable):
        """设置配置更新回调（用于热更新运行中的组件）"""
        self.config_update_callback = callback
    
    async def start(self):
        """启动服务器"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        print(f"{Fore.GREEN}[成功] Web 控制面板已启动: http://{self.host}:{self.port}{Style.RESET_ALL}")
    
    async def stop(self):
        """停止服务器"""
        # 关闭所有 WebSocket 连接
        for ws in list(self.status_clients):
            await ws.close()
        self.status_clients.clear()
        
        if self.runner:
            await self.runner.cleanup()
            print(f"{Fore.CYAN}[信息] Web 服务器已停止{Style.RESET_ALL}")
