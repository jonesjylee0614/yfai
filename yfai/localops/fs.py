"""文件系统操作模块"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileSystemOps:
    """文件系统操作"""

    def __init__(self, whitelist: Optional[List[str]] = None):
        """初始化文件系统操作

        Args:
            whitelist: 允许访问的目录白名单
        """
        self.whitelist = whitelist or []

    def _is_in_whitelist(self, path: str) -> bool:
        """检查路径是否在白名单中

        Args:
            path: 文件路径

        Returns:
            bool: 是否在白名单中
        """
        if not self.whitelist:
            return True  # 无白名单限制

        path_obj = Path(path).resolve()

        for allowed_path in self.whitelist:
            # 替换环境变量
            allowed_path = os.path.expandvars(allowed_path)
            allowed_obj = Path(allowed_path).resolve()

            try:
                # 检查是否在允许的路径下
                path_obj.relative_to(allowed_obj)
                return True
            except ValueError:
                continue

        return False

    def read(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """读取文件

        Args:
            path: 文件路径
            encoding: 编码

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not self._is_in_whitelist(path):
                return {
                    "success": False,
                    "error": f"路径不在白名单中: {path}",
                    "risk_level": "high",
                }

            with open(path, "r", encoding=encoding) as f:
                content = f.read()

            return {
                "success": True,
                "content": content,
                "path": path,
                "size": len(content),
                "risk_level": "low",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

    def write(
        self, path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True
    ) -> Dict[str, Any]:
        """写入文件

        Args:
            path: 文件路径
            content: 文件内容
            encoding: 编码
            create_dirs: 是否创建父目录

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not self._is_in_whitelist(path):
                return {
                    "success": False,
                    "error": f"路径不在白名单中: {path}",
                    "risk_level": "high",
                }

            path_obj = Path(path)

            if create_dirs:
                path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding=encoding) as f:
                f.write(content)

            return {
                "success": True,
                "path": path,
                "size": len(content),
                "risk_level": "medium",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "medium"}

    def list_dir(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """列出目录内容

        Args:
            path: 目录路径
            recursive: 是否递归

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not self._is_in_whitelist(path):
                return {
                    "success": False,
                    "error": f"路径不在白名单中: {path}",
                    "risk_level": "low",
                }

            path_obj = Path(path)
            if not path_obj.exists():
                return {"success": False, "error": "目录不存在", "risk_level": "low"}

            if not path_obj.is_dir():
                return {"success": False, "error": "不是目录", "risk_level": "low"}

            files = []
            if recursive:
                for item in path_obj.rglob("*"):
                    files.append(
                        {
                            "path": str(item),
                            "name": item.name,
                            "is_dir": item.is_dir(),
                            "size": item.stat().st_size if item.is_file() else 0,
                        }
                    )
            else:
                for item in path_obj.iterdir():
                    files.append(
                        {
                            "path": str(item),
                            "name": item.name,
                            "is_dir": item.is_dir(),
                            "size": item.stat().st_size if item.is_file() else 0,
                        }
                    )

            return {
                "success": True,
                "files": files,
                "count": len(files),
                "risk_level": "low",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

    def delete(self, path: str) -> Dict[str, Any]:
        """删除文件或目录

        Args:
            path: 路径

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not self._is_in_whitelist(path):
                return {
                    "success": False,
                    "error": f"路径不在白名单中: {path}",
                    "risk_level": "critical",
                }

            path_obj = Path(path)
            if not path_obj.exists():
                return {"success": False, "error": "路径不存在", "risk_level": "high"}

            if path_obj.is_dir():
                shutil.rmtree(path)
            else:
                path_obj.unlink()

            return {"success": True, "path": path, "risk_level": "high"}
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "high"}

    def search(
        self, path: str, pattern: str, recursive: bool = True
    ) -> Dict[str, Any]:
        """搜索文件

        Args:
            path: 搜索路径
            pattern: 文件名模式 (glob)
            recursive: 是否递归

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if not self._is_in_whitelist(path):
                return {
                    "success": False,
                    "error": f"路径不在白名单中: {path}",
                    "risk_level": "low",
                }

            path_obj = Path(path)
            if not path_obj.exists():
                return {"success": False, "error": "路径不存在", "risk_level": "low"}

            if recursive:
                matches = list(path_obj.rglob(pattern))
            else:
                matches = list(path_obj.glob(pattern))

            results = [
                {
                    "path": str(item),
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                }
                for item in matches
            ]

            return {
                "success": True,
                "results": results,
                "count": len(results),
                "risk_level": "low",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

