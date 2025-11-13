"""MCP服务器注册中心

管理MCP Server的注册、发现和健康检查
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class McpServerConfig:
    """MCP服务器配置"""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.type: str = data["type"]  # local / remote
        self.endpoint: str = data["endpoint"]
        self.auth: Dict[str, Any] = data.get("auth", {})
        self.capabilities: Dict[str, Any] = data.get("capabilities", {})
        self.settings: Dict[str, Any] = data.get("settings", {})
        self.enabled: bool = data.get("enabled", False)
        self.description: str = data.get("description", "")

    def get_tools(self) -> List[str]:
        """获取工具列表"""
        return self.capabilities.get("tools", [])

    def get_timeout(self) -> int:
        """获取超时时间"""
        return self.settings.get("timeout", 30)

    def get_auth_token(self) -> Optional[str]:
        """获取认证Token"""
        auth_type = self.auth.get("type")
        if auth_type == "none":
            return None
        elif auth_type == "bearer":
            token_env = self.auth.get("token_env")
            if token_env:
                return os.getenv(token_env)
        elif auth_type == "api_key":
            key_env = self.auth.get("key_env")
            if key_env:
                return os.getenv(key_env)
        return None


class McpRegistry:
    """MCP服务器注册中心"""

    def __init__(self, config_path: str = "configs/McpRegistry.yaml"):
        self.config_path = Path(config_path)
        self.servers: Dict[str, McpServerConfig] = {}
        self.permissions: Dict[str, List[str]] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置"""
        if not self.config_path.exists():
            print(f"MCP注册配置文件不存在: {self.config_path}")
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 加载服务器配置
        for server_data in config.get("servers", []):
            server = McpServerConfig(server_data)
            self.servers[server.id] = server

        # 加载权限映射
        self.permissions = config.get("permissions", {})

    def get_server(self, server_id: str) -> Optional[McpServerConfig]:
        """获取服务器配置

        Args:
            server_id: 服务器ID

        Returns:
            McpServerConfig: 服务器配置
        """
        return self.servers.get(server_id)

    def list_servers(self, enabled_only: bool = False) -> List[McpServerConfig]:
        """列出所有服务器

        Args:
            enabled_only: 是否只返回已启用的服务器

        Returns:
            List[McpServerConfig]: 服务器列表
        """
        servers = list(self.servers.values())
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return servers

    def list_tools(self, server_id: Optional[str] = None) -> List[str]:
        """列出工具

        Args:
            server_id: 服务器ID，None则返回所有工具

        Returns:
            List[str]: 工具名称列表
        """
        if server_id:
            server = self.get_server(server_id)
            return server.get_tools() if server else []

        # 返回所有工具
        tools = []
        for server in self.servers.values():
            if server.enabled:
                tools.extend(server.get_tools())
        return tools

    def get_tool_risk_level(self, tool_name: str) -> str:
        """获取工具风险等级

        Args:
            tool_name: 工具名称

        Returns:
            str: 风险等级 (low/medium/high/critical)
        """
        # 检查是否在危险操作列表中
        if tool_name in self.permissions.get("dangerous_ops", []):
            return "high"

        # 检查是否在写入操作列表中
        if tool_name in self.permissions.get("write_ops", []):
            return "medium"

        # 检查是否在只读操作列表中
        if tool_name in self.permissions.get("read_only", []):
            return "low"

        # 默认中等风险
        return "medium"

    def should_require_approval(self, tool_name: str) -> bool:
        """判断是否需要审批

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否需要审批
        """
        risk_level = self.get_tool_risk_level(tool_name)
        return risk_level in ["high", "critical"]

    def enable_server(self, server_id: str) -> bool:
        """启用服务器

        Args:
            server_id: 服务器ID

        Returns:
            bool: 是否成功
        """
        server = self.get_server(server_id)
        if server:
            server.enabled = True
            return True
        return False

    def disable_server(self, server_id: str) -> bool:
        """禁用服务器

        Args:
            server_id: 服务器ID

        Returns:
            bool: 是否成功
        """
        server = self.get_server(server_id)
        if server:
            server.enabled = False
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        enabled_servers = [s for s in self.servers.values() if s.enabled]
        return {
            "total_servers": len(self.servers),
            "enabled_servers": len(enabled_servers),
            "total_tools": len(self.list_tools()),
        }

