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
        self.custom_models: Dict[str, List[Dict[str, str]]] = {}
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
                    api_key=bailian_config.get("api_key"),
                    default_model=bailian_config.get("default_model", "qwen-plus"),
                    timeout=bailian_config.get("timeout", 60),
                    max_retries=bailian_config.get("max_retries", 3),
                )
                self.health_status["bailian"] = False
                self.custom_models["bailian"] = bailian_config.get("models", []) or []
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
                self.custom_models["ollama"] = ollama_config.get("models", []) or []
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
        """获取Provider"""
        _, provider = self._resolve_provider(name)
        return provider

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
        resolved_name, provider = self._resolve_provider(provider_name)
        if not provider:
            print(f"Provider {provider_name} 不存在")
            return None

        try:
            response = await provider.chat(messages, **kwargs)
            if response:
                response.provider = resolved_name
            return response
        except Exception as e:
            print(f"Provider {resolved_name} 调用失败: {e}")

            # 尝试降级
            if resolved_name != "ollama" and "ollama" in self.providers:
                print("尝试降级到Ollama...")
                try:
                    response = await self.providers["ollama"].chat(messages, **kwargs)
                    if response:
                        response.provider = "ollama"
                    return response
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
                extra = self._format_custom_models(name)
                merged = self._merge_models(models, extra)
                result[name] = merged
            except Exception as e:
                print(f"获取 {name} 模型列表失败: {e}")
                result[name] = self._format_custom_models(name)

        return result

    def get_health_status(self) -> Dict[str, bool]:
        """获取健康状态

        Returns:
            Dict[str, bool]: Provider名称 -> 健康状态
        """
        return self.health_status.copy()

    def get_default_model(self, provider_name: Optional[str]) -> Optional[str]:
        """获取指定 Provider 的默认模型"""
        if not provider_name:
            return None
        provider = self.providers.get(provider_name)
        if provider and getattr(provider, "default_model", None):
            return provider.default_model
        # 回退到配置
        return (
            self.config.get("providers", {})
            .get(provider_name, {})
            .get("default_model")
        )

    def get_configured_models(self, provider_name: Optional[str] = None) -> List[Dict[str, str]]:
        """获取配置中维护的模型元数据"""
        if provider_name:
            return self.custom_models.get(provider_name, [])
        merged: List[Dict[str, str]] = []
        for items in self.custom_models.values():
            merged.extend(items)
        return merged

    def _format_custom_models(self, provider_name: str) -> List[str]:
        """将自定义模型转换为可读名称"""
        formatted: List[str] = []
        for item in self.custom_models.get(provider_name, []):
            code = item.get("code", "")
            name = item.get("name", "")
            if code and name:
                formatted.append(f"{code} ({name})")
            elif code:
                formatted.append(code)
        return formatted

    @staticmethod
    def _merge_models(remote: List[str], extra: List[str]) -> List[str]:
        """合并远端模型和自定义模型列表"""
        seen = set()
        merged: List[str] = []
        for name in remote + extra:
            if not name:
                continue
            if name in seen:
                continue
            merged.append(name)
            seen.add(name)
        return merged

    def get_default_provider_name(self) -> Optional[str]:
        """返回配置中的默认 Provider 名称"""
        default_provider = self.config.get("app", {}).get("default_provider", "bailian")
        if default_provider == "auto":
            # auto 目前回退到百炼，如果不存在则取第一个
            if "bailian" in self.providers:
                default_provider = "bailian"
            elif "ollama" in self.providers:
                default_provider = "ollama"
        if default_provider in self.providers:
            return default_provider
        return next(iter(self.providers.keys()), None)

    def _resolve_provider(self, name: Optional[str]) -> tuple[Optional[str], Optional[BaseProvider]]:
        """解析需要使用的 Provider 名称和实例"""
        if name and name in self.providers:
            return name, self.providers[name]
        default_name = self.get_default_provider_name()
        if not default_name:
            return None, None
        return default_name, self.providers.get(default_name)

