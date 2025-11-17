"""搜索管理器"""

from typing import Dict, List, Optional, Any
from .base import SearchAdapter, SearchResult
from .adapters import DuckDuckGoAdapter, BingAdapter, GoogleAdapter


class SearchManager:
    """搜索管理器 - 管理多个搜索适配器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.adapters: Dict[str, SearchAdapter] = {}
        self._init_adapters()

    def _init_adapters(self):
        """初始化搜索适配器"""
        search_config = self.config.get("search", {})

        # 初始化 DuckDuckGo（免费，无需 API Key）
        if search_config.get("duckduckgo", {}).get("enabled", True):
            self.adapters["duckduckgo"] = DuckDuckGoAdapter(
                search_config.get("duckduckgo", {})
            )

        # 初始化 Bing（需要 API Key）
        if search_config.get("bing", {}).get("enabled", False):
            bing_config = search_config.get("bing", {})
            if bing_config.get("api_key"):
                self.adapters["bing"] = BingAdapter(bing_config)

        # 初始化 Google（需要 API Key 和 Search Engine ID）
        if search_config.get("google", {}).get("enabled", False):
            google_config = search_config.get("google", {})
            if google_config.get("api_key") and google_config.get("search_engine_id"):
                self.adapters["google"] = GoogleAdapter(google_config)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        engine: Optional[str] = None,
        **kwargs
    ) -> List[SearchResult]:
        """执行搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数
            engine: 指定搜索引擎，None 则使用默认引擎
            **kwargs: 其他参数

        Returns:
            搜索结果列表
        """
        # 如果指定了搜索引擎
        if engine and engine in self.adapters:
            adapter = self.adapters[engine]
            return await adapter.search(query, max_results, **kwargs)

        # 使用默认搜索引擎（按优先级）
        priority = self.config.get("search", {}).get("priority", ["google", "bing", "duckduckgo"])

        for engine_name in priority:
            if engine_name in self.adapters:
                adapter = self.adapters[engine_name]
                try:
                    results = await adapter.search(query, max_results, **kwargs)
                    if results:
                        return results
                except Exception as e:
                    print(f"搜索引擎 {engine_name} 失败: {e}")
                    continue

        # 如果所有引擎都失败，返回空列表
        print("⚠️ 所有搜索引擎均不可用")
        return []

    async def search_multiple(
        self,
        query: str,
        max_results_per_engine: int = 3,
        engines: Optional[List[str]] = None,
    ) -> Dict[str, List[SearchResult]]:
        """使用多个搜索引擎并行搜索

        Args:
            query: 搜索查询
            max_results_per_engine: 每个引擎的最大结果数
            engines: 要使用的搜索引擎列表，None 则使用所有可用引擎

        Returns:
            {engine_name: [results]} 的字典
        """
        import asyncio

        engines_to_use = engines if engines else list(self.adapters.keys())

        tasks = []
        engine_names = []

        for engine_name in engines_to_use:
            if engine_name in self.adapters:
                adapter = self.adapters[engine_name]
                tasks.append(adapter.search(query, max_results_per_engine))
                engine_names.append(engine_name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            name: result if not isinstance(result, Exception) else []
            for name, result in zip(engine_names, results)
        }

    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有搜索引擎健康状态

        Returns:
            {engine_name: is_healthy} 的字典
        """
        import asyncio

        tasks = []
        engine_names = []

        for name, adapter in self.adapters.items():
            tasks.append(adapter.health_check())
            engine_names.append(name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            name: result if not isinstance(result, Exception) else False
            for name, result in zip(engine_names, results)
        }

    def get_available_engines(self) -> List[str]:
        """获取可用的搜索引擎列表

        Returns:
            搜索引擎名称列表
        """
        return list(self.adapters.keys())

    def add_adapter(self, name: str, adapter: SearchAdapter):
        """添加自定义搜索适配器

        Args:
            name: 适配器名称
            adapter: 适配器实例
        """
        self.adapters[name] = adapter

    def remove_adapter(self, name: str):
        """移除搜索适配器

        Args:
            name: 适配器名称
        """
        if name in self.adapters:
            del self.adapters[name]
