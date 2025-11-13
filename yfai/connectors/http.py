"""HTTP 连接器"""

import httpx
from typing import Any, Dict
from .base import BaseConnector


class HttpConnector(BaseConnector):
    """HTTP API 连接器"""

    async def connect(self) -> bool:
        """建立连接"""
        self.connected = True
        return True

    async def disconnect(self) -> bool:
        """断开连接"""
        self.connected = False
        return True

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            base_url = self.config.get("base_url", "")
            if not base_url:
                return {"success": False, "error": "Missing base_url"}

            async with httpx.AsyncClient() as client:
                response = await client.get(base_url, timeout=10)
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def call(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用 HTTP 方法"""
        try:
            base_url = self.config.get("base_url", "")
            method = params.get("method", "GET").upper()
            path = params.get("path", "")
            headers = params.get("headers", {})
            data = params.get("data")

            url = f"{base_url}{path}"

            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {"success": False, "error": f"Unsupported method: {method}"}

                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
