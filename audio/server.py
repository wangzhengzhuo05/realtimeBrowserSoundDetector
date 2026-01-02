# -*- coding: utf-8 -*-
"""
WebSocket 音频服务器
接收来自浏览器插件的音频数据
"""

import asyncio
from typing import Callable, Optional

from colorama import Fore, Style

try:
    import websockets
except ImportError:
    print(f"{Fore.RED}[错误] 请安装 websockets 库: pip install websockets{Style.RESET_ALL}")
    raise


class AudioWebSocketServer:
    """
    WebSocket 服务器
    接收浏览器插件发送的音频数据
    """
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.audio_callback: Optional[Callable[[bytes], None]] = None
        self.server = None
        self.is_running = False
        self.connected_clients = set()
        
    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """设置音频数据回调函数"""
        self.audio_callback = callback
    
    async def _handle_client(self, websocket):
        """处理客户端连接"""
        client_id = id(websocket)
        self.connected_clients.add(websocket)
        
        print(f"{Fore.GREEN}[WS] 浏览器插件已连接 (客户端 #{client_id}){Style.RESET_ALL}")
        
        try:
            async for message in websocket:
                # 接收音频数据 (bytes)
                if isinstance(message, bytes) and self.audio_callback:
                    self.audio_callback(message)
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"{Fore.YELLOW}[WS] 客户端 #{client_id} 断开连接{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[WS] 处理客户端数据时出错: {e}{Style.RESET_ALL}")
        finally:
            self.connected_clients.discard(websocket)
    
    async def _run_server(self):
        """运行 WebSocket 服务器"""
        try:
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            self.is_running = True
            
            print(f"{Fore.GREEN}[成功] WebSocket 服务器已启动: ws://{self.host}:{self.port}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[提示] 请在浏览器中安装插件并连接到此地址{Style.RESET_ALL}")
            
            # 保持服务器运行
            await self.server.wait_closed()
            
        except Exception as e:
            print(f"{Fore.RED}[错误] WebSocket 服务器启动失败: {e}{Style.RESET_ALL}")
            raise
    
    def start(self):
        """启动服务器（在新的事件循环中）"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run_server())
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    async def start_async(self):
        """异步启动服务器"""
        await self._run_server()
    
    def stop(self):
        """停止服务器"""
        self.is_running = False
        if self.server:
            self.server.close()
            print(f"{Fore.CYAN}[信息] WebSocket 服务器已停止{Style.RESET_ALL}")
    
    async def send_to_clients(self, message: str):
        """向所有连接的客户端发送消息"""
        if self.connected_clients:
            await asyncio.gather(
                *[client.send(message) for client in self.connected_clients],
                return_exceptions=True
            )
