"""Provider管理器

负责Provider的注册、选择、健康检查、降级等
"""

import asyncio
from typing import Dict, List, Optional

from .base import BaseProvider, ChatMessage, ChatResponse, ProviderType
from .bailian import BailianProvider
from .ollama import OllamaProvider


class ProviderManager:
    """Provider管理器"""

    def __init__(self, config: Dict):
        self.config = config
        self.providers: Dict[str, BaseProvider] = {}
        self.health_status: Dict[str, bool] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        """初始化Provider"""
        providers_config = self.config.get("providers", {})

        # 初始化百炼
        if "bailian" in providers_config:
            bailian_config = providers_config["bailian"]
            try:
                self.providers["bailian"] = BailianProvider(
                    api_base=bailian_config.get(
                        "api_base", "https://dashscope.aliyuncs.com/compatible-mode/v1"
                    ),
                    default_model=bailian_config.get("default_model", "qwen-plus"),
                    timeout=bailian_config.get("timeout", 60),
                    max_retries=bailian_config.get("max_retries", 3),
                )
                self.health_status["bailian"] = False
            except Exception as e:
                print(f"初始化百炼Provider失败: {e}")

        # 初始化Ollama
        if "ollama" in providers_config:
            ollama_config = providers_config["ollama"]
            try:
                self.providers["ollama"] = OllamaProvider(
                    api_base=ollama_config.get("api_base", "http://127.0.0.1:11434"),
                    default_model=ollama_config.get("default_model", "qwen2.5-coder"),
                    timeout=ollama_config.get("timeout", 120),
                    max_retries=ollama_config.get("max_retries", 3),
                )
                self.health_status["ollama"] = False
            except Exception as e:
                print(f"初始化Ollama Provider失败: {e}")

    async def check_health_all(self) -> Dict[str, bool]:
        """检查所有Provider健康状态

        Returns:
            Dict[str, bool]: Provider名称 -> 健康状态
        """
        tasks = []
        names = []

        for name, provider in self.providers.items():
            tasks.append(provider.health_check())
            names.append(name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(names, results):
            if isinstance(result, Exception):
                self.health_status[name] = False
            else:
                self.health_status[name] = result

        return self.health_status

    def get_provider(self, name: Optional[str] = None) -> Optional[BaseProvider]:
        """获取Provider

        Args:
            name: Provider名称，None则返回默认Provider

        Returns:
            BaseProvider: Provider实例
        """
        if name is None:
            # 获取默认Provider
            default_provider = self.config.get("app", {}).get(
                "default_provider", "bailian"
            )
            name = default_provider

        return self.providers.get(name)

    def get_provider_by_route(self, task_type: str) -> Optional[BaseProvider]:
        """根据任务类型路由到合适的Provider

        Args:
            task_type: 任务类型 (coding/general/offline_only等)

        Returns:
            BaseProvider: Provider实例
        """
        model_route = self.config.get("app", {}).get("model_route", {})
        route = model_route.get(task_type)

        if route:
            # 解析路由: "provider:model"
            parts = route.split(":")
            if len(parts) == 2:
                provider_name, model = parts
                provider = self.get_provider(provider_name)
                if provider:
                    # 临时设置模型
                    provider.default_model = model
                    return provider

        # 降级到默认Provider
        return self.get_provider()

    async def chat(
        self,
        messages: List[ChatMessage],
        provider_name: Optional[str] = None,
        **kwargs,
    ) -> Optional[ChatResponse]:
        """发送聊天请求（带降级）

        Args:
            messages: 消息列表
            provider_name: Provider名称
            **kwargs: 其他参数

        Returns:
            ChatResponse: 响应对象
        """
        provider = self.get_provider(provider_name)
        if not provider:
            print(f"Provider {provider_name} 不存在")
            return None

        try:
            return await provider.chat(messages, **kwargs)
        except Exception as e:
            print(f"Provider {provider_name} 调用失败: {e}")

            # 尝试降级
            if provider_name != "ollama" and "ollama" in self.providers:
                print("尝试降级到Ollama...")
                try:
                    return await self.providers["ollama"].chat(messages, **kwargs)
                except Exception as e2:
                    print(f"降级失败: {e2}")

            return None

    async def list_all_models(self) -> Dict[str, List[str]]:
        """列出所有Provider的可用模型

        Returns:
            Dict[str, List[str]]: Provider名称 -> 模型列表
        """
        result = {}

        for name, provider in self.providers.items():
            try:
                models = await provider.list_models()
                result[name] = models
            except Exception as e:
                print(f"获取 {name} 模型列表失败: {e}")
                result[name] = []

        return result

    def get_health_status(self) -> Dict[str, bool]:
        """获取健康状态

        Returns:
            Dict[str, bool]: Provider名称 -> 健康状态
        """
        return self.health_status.copy()

