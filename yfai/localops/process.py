"""进程管理模块"""

from typing import Any, Dict, List, Optional

import psutil


class ProcessOps:
    """进程操作"""

    def list_processes(
        self, sort_by: str = "cpu", limit: int = 50
    ) -> Dict[str, Any]:
        """列出进程

        Args:
            sort_by: 排序字段 (cpu/memory/name)
            limit: 返回数量限制

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            processes = []

            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_percent", "status", "username"]
            ):
                try:
                    info = proc.info
                    processes.append(
                        {
                            "pid": info["pid"],
                            "name": info["name"],
                            "cpu_percent": info.get("cpu_percent", 0),
                            "memory_percent": info.get("memory_percent", 0),
                            "status": info.get("status", "unknown"),
                            "username": info.get("username", "unknown"),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 排序
            if sort_by == "cpu":
                processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x["memory_percent"], reverse=True)
            elif sort_by == "name":
                processes.sort(key=lambda x: x["name"])

            # 限制数量
            processes = processes[:limit]

            return {
                "success": True,
                "processes": processes,
                "count": len(processes),
                "risk_level": "low",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

    def get_process(self, pid: int) -> Dict[str, Any]:
        """获取进程信息

        Args:
            pid: 进程ID

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            proc = psutil.Process(pid)

            info = {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_percent": proc.memory_percent(),
                "memory_info": proc.memory_info()._asdict(),
                "create_time": proc.create_time(),
                "username": proc.username(),
                "cwd": proc.cwd(),
                "cmdline": proc.cmdline(),
                "connections": len(proc.connections()),
                "num_threads": proc.num_threads(),
            }

            return {"success": True, "process": info, "risk_level": "low"}

        except psutil.NoSuchProcess:
            return {"success": False, "error": "进程不存在", "risk_level": "low"}
        except psutil.AccessDenied:
            return {"success": False, "error": "没有权限访问进程", "risk_level": "low"}
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

    def kill_process(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """终止进程

        Args:
            pid: 进程ID
            force: 是否强制终止

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            proc = psutil.Process(pid)
            name = proc.name()

            if force:
                proc.kill()
            else:
                proc.terminate()

            # 等待进程退出
            proc.wait(timeout=5)

            return {
                "success": True,
                "pid": pid,
                "name": name,
                "method": "kill" if force else "terminate",
                "risk_level": "high",
            }

        except psutil.NoSuchProcess:
            return {"success": False, "error": "进程不存在", "risk_level": "high"}
        except psutil.AccessDenied:
            return {"success": False, "error": "没有权限终止进程", "risk_level": "high"}
        except psutil.TimeoutExpired:
            return {"success": False, "error": "进程终止超时", "risk_level": "high"}
        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "high"}

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息

        Returns:
            Dict[str, Any]: 系统信息
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            info = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(logical=True),
                    "physical_count": psutil.cpu_count(logical=False),
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                },
                "boot_time": psutil.boot_time(),
            }

            return {"success": True, "system": info, "risk_level": "low"}

        except Exception as e:
            return {"success": False, "error": str(e), "risk_level": "low"}

