"""搜索适配器基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class SearchResult:
    """搜索结果"""

    title: str
    url: str
    snippet: str
    source: str  # 搜索引擎名称
    relevance_score: Optional[float] = None
    published_date: Optional[datetime] = None
    author: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "author": self.author,
            "metadata": self.metadata or {},
        }


class SearchAdapter(ABC):
    """搜索适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """执行搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数
            **kwargs: 其他参数

        Returns:
            搜索结果列表
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查

        Returns:
            是否健康
        """
        pass

    def get_name(self) -> str:
        """获取适配器名称"""
        return self.name
