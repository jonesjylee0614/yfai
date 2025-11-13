"""Ollama本地模型提供商适配器"""

from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseProvider, ChatMessage, ChatResponse, ProviderType


class OllamaProvider(BaseProvider):
    """Ollama Provider实现"""

    def __init__(
        self,
        api_base: str = "http://127.0.0.1:11434",
        default_model: str = "qwen2.5-coder",
        timeout: int = 120,
        max_retries: int = 3,
    ):
        super().__init__(api_base, None, default_model, timeout, max_retries)

    def get_provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA

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
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in messages
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            data["options"]["num_predict"] = max_tokens

        # 发送请求
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base}/api/chat",
                json=data,
            )
            response.raise_for_status()
            result = response.json()

        # 解析响应
        message = result.get("message", {})
        return ChatResponse(
            content=message.get("content", ""),
            role=message.get("role", "assistant"),
            finish_reason=result.get("done_reason"),
            tool_calls=None,  # Ollama暂不支持工具调用
            usage={
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0)
                + result.get("eval_count", 0),
            },
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
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in messages
            ],
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            data["options"]["num_predict"] = max_tokens

        # 发送流式请求
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/api/chat",
                json=data,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json

                            chunk = json.loads(line)
                            message = chunk.get("message", {})
                            content = message.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.api_base}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """列出可用模型"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_base}/api/tags")
                response.raise_for_status()
                result = response.json()
                return [model["name"] for model in result.get("models", [])]
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []

    async def pull_model(self, model: str) -> bool:
        """拉取模型

        Args:
            model: 模型名称

        Returns:
            bool: 是否成功
        """
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                response = await client.post(
                    f"{self.api_base}/api/pull",
                    json={"name": model},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"拉取模型失败: {e}")
            return False

