"""连接器基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseConnector(ABC):
    """连接器基类"""

    def __init__(self, config: Dict[str, Any]):
        """初始化连接器

        Args:
            config: 连接配置
        """
        self.config = config
        self.connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接

        Returns:
            测试结果
        """
        pass

    @abstractmethod
    async def call(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用连接器方法

        Args:
            action: 操作名称
            params: 参数

        Returns:
            执行结果
        """
        pass
