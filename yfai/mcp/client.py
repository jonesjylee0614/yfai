"""MCP客户端

与MCP Server通信的客户端实现
"""

import json
from typing import Any, Dict, List, Optional

import httpx


class McpClient:
    """MCP客户端"""

    def __init__(self, endpoint: str, auth_token: Optional[str] = None, timeout: int = 30):
        """初始化MCP客户端

        Args:
            endpoint: MCP服务器端点
            auth_token: 认证Token
            timeout: 超时时间(秒)
        """
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.timeout = timeout
        self.session_id: Optional[str] = None

    async def connect(self) -> bool:
        """连接到MCP服务器

        Returns:
            bool: 是否连接成功
        """
        try:
            # 目前使用HTTP模拟，实际应该使用WebSocket
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                # 尝试连接并获取能力
                response = await client.get(
                    f"{self.endpoint}/capabilities", headers=headers
                )
                return response.status_code == 200
        except Exception as e:
            print(f"连接MCP服务器失败: {e}")
            return False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用工具

        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                response = await client.get(f"{self.endpoint}/tools", headers=headers)
                response.raise_for_status()
                return response.json().get("tools", [])
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []

    async def call_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """调用工具

        Args:
            tool_name: 工具名称
            params: 参数字典

        Returns:
            Dict[str, Any]: 工具执行结果
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Content-Type": "application/json"}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                data = {"tool": tool_name, "params": params}

                response = await client.post(
                    f"{self.endpoint}/tool/call", headers=headers, json=data
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"调用工具失败: {e}")
            return None

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 是否健康
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                response = await client.get(f"{self.endpoint}/health", headers=headers)
                return response.status_code == 200
        except Exception:
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        # 清理资源
        self.session_id = None

    def __repr__(self) -> str:
        return f"McpClient(endpoint='{self.endpoint}')"

