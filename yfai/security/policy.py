"""安全策略模块"""

from typing import Any, Dict, List


class SecurityPolicy:
    """安全策略"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dangerous_ops = (
            config.get("local_ops", {}).get("dangerous_ops", {}).get("require_approval", [])
        )
        self.roots_whitelist = config.get("local_ops", {}).get("roots_whitelist", [])

    def is_dangerous_operation(self, operation: str) -> bool:
        """判断是否为危险操作

        Args:
            operation: 操作名称

        Returns:
            bool: 是否危险
        """
        return operation in self.dangerous_ops

    def is_path_allowed(self, path: str) -> bool:
        """判断路径是否在白名单中

        Args:
            path: 文件路径

        Returns:
            bool: 是否允许
        """
        if not self.roots_whitelist:
            return True

        from pathlib import Path
        import os

        path_obj = Path(path).resolve()

        for allowed in self.roots_whitelist:
            allowed = os.path.expandvars(allowed)
            allowed_obj = Path(allowed).resolve()

            try:
                path_obj.relative_to(allowed_obj)
                return True
            except ValueError:
                continue

        return False

    def get_operation_risk_level(self, operation: str) -> str:
        """获取操作风险等级

        Args:
            operation: 操作名称

        Returns:
            str: 风险等级
        """
        if operation in self.dangerous_ops:
            # 根据操作类型判断
            if "delete" in operation or "kill" in operation:
                return "high"
            elif "write" in operation or "exec" in operation:
                return "medium"
            else:
                return "medium"

        if "read" in operation or "list" in operation or "get" in operation:
            return "low"

        return "medium"

