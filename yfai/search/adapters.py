"""内置搜索适配器"""

import httpx
from typing import List, Dict, Any
from .base import SearchAdapter, SearchResult


class DuckDuckGoAdapter(SearchAdapter):
    """DuckDuckGo 搜索适配器（使用免费 API）"""

    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """执行 DuckDuckGo 搜索"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 使用 DuckDuckGo Instant Answer API
                params = {
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                }
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params=params
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                results = []

                # 解析结果
                if data.get("Abstract"):
                    results.append(SearchResult(
                        title=data.get("Heading", query),
                        url=data.get("AbstractURL", ""),
                        snippet=data.get("Abstract", ""),
                        source="duckduckgo",
                        metadata={
                            "image": data.get("Image"),
                            "answer_type": data.get("AnswerType"),
                        }
                    ))

                # 添加相关主题
                for topic in data.get("RelatedTopics", [])[:max_results - 1]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append(SearchResult(
                            title=topic.get("Text", "")[:100],
                            url=topic.get("FirstURL", ""),
                            snippet=topic.get("Text", ""),
                            source="duckduckgo",
                        ))

                return results[:max_results]

        except Exception as e:
            print(f"DuckDuckGo 搜索失败: {e}")
            return []

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("https://api.duckduckgo.com/?q=test&format=json")
                return response.status_code == 200
        except:
            return False


class BingAdapter(SearchAdapter):
    """Bing 搜索适配器（需要 API Key）"""

    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """执行 Bing 搜索"""
        api_key = self.config.get("api_key")
        if not api_key:
            print("Bing 搜索需要 API Key，请在配置中设置")
            return []

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"Ocp-Apim-Subscription-Key": api_key}
                params = {
                    "q": query,
                    "count": max_results,
                    "mkt": self.config.get("market", "zh-CN"),
                }

                response = await client.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    headers=headers,
                    params=params
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                results = []

                for item in data.get("webPages", {}).get("value", []):
                    results.append(SearchResult(
                        title=item.get("name", ""),
                        url=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                        source="bing",
                        published_date=item.get("dateLastCrawled"),
                    ))

                return results[:max_results]

        except Exception as e:
            print(f"Bing 搜索失败: {e}")
            return []

    async def health_check(self) -> bool:
        """健康检查"""
        api_key = self.config.get("api_key")
        if not api_key:
            return False

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {"Ocp-Apim-Subscription-Key": api_key}
                response = await client.get(
                    "https://api.bing.microsoft.com/v7.0/search?q=test&count=1",
                    headers=headers
                )
                return response.status_code == 200
        except:
            return False


class GoogleAdapter(SearchAdapter):
    """Google 自定义搜索适配器（需要 API Key 和 Search Engine ID）"""

    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """执行 Google 搜索"""
        api_key = self.config.get("api_key")
        search_engine_id = self.config.get("search_engine_id")

        if not api_key or not search_engine_id:
            print("Google 搜索需要 API Key 和 Search Engine ID")
            return []

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                params = {
                    "key": api_key,
                    "cx": search_engine_id,
                    "q": query,
                    "num": min(max_results, 10),  # Google API 限制
                }

                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                results = []

                for item in data.get("items", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="google",
                        metadata={
                            "display_link": item.get("displayLink"),
                            "formatted_url": item.get("formattedUrl"),
                        }
                    ))

                return results[:max_results]

        except Exception as e:
            print(f"Google 搜索失败: {e}")
            return []

    async def health_check(self) -> bool:
        """健康检查"""
        api_key = self.config.get("api_key")
        search_engine_id = self.config.get("search_engine_id")

        if not api_key or not search_engine_id:
            return False

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                params = {
                    "key": api_key,
                    "cx": search_engine_id,
                    "q": "test",
                    "num": 1,
                }
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params
                )
                return response.status_code == 200
        except:
            return False
