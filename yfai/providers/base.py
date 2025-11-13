"""Provider基础接口定义"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """提供商类型"""

    BAILIAN = "bailian"
    OLLAMA = "ollama"
    OPENAI = "openai"


class ChatMessage(BaseModel):
    """聊天消息"""

    role: str = Field(..., description="角色: user/assistant/system/tool")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="发送者名称")
    tool_call_id: Optional[str] = Field(None, description="工具调用ID")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用列表")


class ChatResponse(BaseModel):
    """聊天响应"""

    content: str = Field(..., description="响应内容")
    role: str = Field(default="assistant", description="角色")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用")
    usage: Optional[Dict[str, int]] = Field(None, description="Token使用统计")
    model: Optional[str] = Field(None, description="使用的模型")


class BaseProvider(ABC):
    """LLM Provider基础抽象类"""

    def __init__(
        self,
        api_base: str,
        api_key: Optional[str] = None,
        default_model: str = "default",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.api_base = api_base
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
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
        """发送聊天请求

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            tools: 工具定义列表
            tool_choice: 工具选择策略
            stream: 是否流式输出
            **kwargs: 其他参数

        Returns:
            ChatResponse: 响应对象
        """
        pass

    @abstractmethod
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
        """流式聊天

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            tools: 工具定义列表
            tool_choice: 工具选择策略
            **kwargs: 其他参数

        Yields:
            str: 流式输出的文本片段
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 是否健康
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """列出可用模型

        Returns:
            List[str]: 模型列表
        """
        pass

    def get_provider_type(self) -> ProviderType:
        """获取Provider类型

        Returns:
            ProviderType: Provider类型
        """
        return ProviderType.BAILIAN  # 子类需要覆盖

