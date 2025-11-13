"""阿里百炼(DashScope)提供商适配器"""

import os
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseProvider, ChatMessage, ChatResponse, ProviderType


class BailianProvider(BaseProvider):
    """阿里百炼Provider实现"""

    def __init__(
        self,
        api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key: Optional[str] = None,
        default_model: str = "qwen-plus",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        # 从环境变量获取API Key
        if api_key is None:
            api_key = os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError("百炼API Key未设置，请设置DASHSCOPE_API_KEY环境变量")

        super().__init__(api_base, api_key, default_model, timeout, max_retries)

    def get_provider_type(self) -> ProviderType:
        return ProviderType.BAILIAN

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        stream: bool = False,
        **kwargs,
    ) -> ChatResponse:
        """发送聊天请求"""
        model = model or self.default_model

        # 构建请求数据
        data = {
            "model": model,
            "messages": [msg.model_dump(exclude_none=True) for msg in messages],
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            data["max_tokens"] = max_tokens

        if tools:
            data["tools"] = tools

        if tool_choice:
            data["tool_choice"] = tool_choice

        # 发送请求
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                json=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()

        # 解析响应
        choice = result["choices"][0]
        message = choice["message"]

        return ChatResponse(
            content=message.get("content", ""),
            role=message.get("role", "assistant"),
            finish_reason=choice.get("finish_reason"),
            tool_calls=message.get("tool_calls"),
            usage=result.get("usage"),
            model=result.get("model"),
        )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        model = model or self.default_model

        # 构建请求数据
        data = {
            "model": model,
            "messages": [msg.model_dump(exclude_none=True) for msg in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            data["max_tokens"] = max_tokens

        if tools:
            data["tools"] = tools

        if tool_choice:
            data["tool_choice"] = tool_choice

        # 发送流式请求
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                json=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # 去掉 "data: " 前缀
                        if data_str == "[DONE]":
                            break

                        try:
                            import json

                            chunk = json.loads(data_str)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.api_base}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """列出可用模型"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.api_base}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                result = response.json()
                return [model["id"] for model in result.get("data", [])]
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return [
                "qwen-plus",
                "qwen-turbo",
                "qwen-max",
                "qwen-max-longcontext",
            ]

