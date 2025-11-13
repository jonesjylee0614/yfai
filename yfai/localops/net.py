"""网络工具模块"""

import socket
from typing import Any, Dict, List, Optional

import httpx


class NetworkOps:
    """网络操作"""

    async def http_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """发送HTTP请求

        Args:
            url: URL
            method: HTTP方法
            headers: 请求头
            data: 请求数据
            timeout: 超时时间

        Returns:
            Dict[str, Any]: 响应结果
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {
                        "success": False,
                        "error": f"不支持的HTTP方法: {method}",
                        "risk_level": "low",
                    }

                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                    "url": url,
                    "method": method,
                    "risk_level": "low",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "method": method,
                "risk_level": "low",
            }

    def check_port(self, host: str, port: int, timeout: float = 2.0) -> Dict[str, Any]:
        """检查端口是否开放

        Args:
            host: 主机地址
            port: 端口号
            timeout: 超时时间

        Returns:
            Dict[str, Any]: 检查结果
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()

            is_open = result == 0

            return {
                "success": True,
                "host": host,
                "port": port,
                "is_open": is_open,
                "risk_level": "low",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "host": host,
                "port": port,
                "risk_level": "low",
            }

    def scan_ports(
        self, host: str, start_port: int = 1, end_port: int = 1024
    ) -> Dict[str, Any]:
        """扫描端口范围

        Args:
            host: 主机地址
            start_port: 起始端口
            end_port: 结束端口

        Returns:
            Dict[str, Any]: 扫描结果
        """
        try:
            open_ports = []

            for port in range(start_port, end_port + 1):
                result = self.check_port(host, port, timeout=0.5)
                if result.get("is_open"):
                    open_ports.append(port)

            return {
                "success": True,
                "host": host,
                "port_range": f"{start_port}-{end_port}",
                "open_ports": open_ports,
                "count": len(open_ports),
                "risk_level": "low",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

    def get_local_ip(self) -> Dict[str, Any]:
        """获取本机IP地址

        Returns:
            Dict[str, Any]: IP地址信息
        """
        try:
            # 通过连接外部地址获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # 获取主机名
            hostname = socket.gethostname()

            return {
                "success": True,
                "local_ip": local_ip,
                "hostname": hostname,
                "risk_level": "low",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

    def resolve_hostname(self, hostname: str) -> Dict[str, Any]:
        """解析主机名

        Args:
            hostname: 主机名

        Returns:
            Dict[str, Any]: 解析结果
        """
        try:
            ip_address = socket.gethostbyname(hostname)

            return {
                "success": True,
                "hostname": hostname,
                "ip_address": ip_address,
                "risk_level": "low",
            }

        except socket.gaierror:
            return {
                "success": False,
                "error": "无法解析主机名",
                "hostname": hostname,
                "risk_level": "low",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

