"""Shell脚本执行模块"""

import asyncio
import platform
import subprocess
from typing import Any, Dict, List, Optional


class ShellOps:
    """Shell操作"""

    def __init__(
        self,
        default_shell: str = "powershell",
        timeout: int = 300,
        wsl_enabled: bool = False,
    ):
        """初始化Shell操作

        Args:
            default_shell: 默认Shell (powershell/bash/cmd)
            timeout: 超时时间(秒)
            wsl_enabled: 是否启用WSL
        """
        self.default_shell = default_shell
        self.timeout = timeout
        self.wsl_enabled = wsl_enabled

    def _get_shell_command(self, shell: str) -> List[str]:
        """获取Shell命令

        Args:
            shell: Shell类型

        Returns:
            List[str]: Shell命令
        """
        if shell == "powershell":
            return ["powershell.exe", "-Command"]
        elif shell == "bash":
            if platform.system() == "Windows" and self.wsl_enabled:
                return ["wsl", "bash", "-c"]
            else:
                return ["bash", "-c"]
        elif shell == "cmd":
            return ["cmd.exe", "/c"]
        else:
            raise ValueError(f"不支持的Shell类型: {shell}")

    async def execute(
        self,
        command: str,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """执行Shell命令

        Args:
            command: 命令字符串
            shell: Shell类型
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间

        Returns:
            Dict[str, Any]: 执行结果
        """
        shell = shell or self.default_shell
        timeout = timeout or self.timeout

        try:
            # 构建命令
            shell_cmd = self._get_shell_command(shell)
            full_command = shell_cmd + [command]

            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                exit_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"命令执行超时({timeout}秒)",
                    "exit_code": -1,
                    "risk_level": "medium",
                }

            return {
                "success": exit_code == 0,
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "exit_code": exit_code,
                "command": command,
                "shell": shell,
                "risk_level": "medium",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exit_code": -1,
                "risk_level": "medium",
            }

    def execute_sync(
        self,
        command: str,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """同步执行Shell命令

        Args:
            command: 命令字符串
            shell: Shell类型
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间

        Returns:
            Dict[str, Any]: 执行结果
        """
        shell = shell or self.default_shell
        timeout = timeout or self.timeout

        try:
            # 构建命令
            shell_cmd = self._get_shell_command(shell)
            full_command = shell_cmd + [command]

            # 执行命令
            result = subprocess.run(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                timeout=timeout,
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.decode("utf-8", errors="ignore"),
                "stderr": result.stderr.decode("utf-8", errors="ignore"),
                "exit_code": result.returncode,
                "command": command,
                "shell": shell,
                "risk_level": "medium",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"命令执行超时({timeout}秒)",
                "exit_code": -1,
                "risk_level": "medium",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exit_code": -1,
                "risk_level": "medium",
            }

