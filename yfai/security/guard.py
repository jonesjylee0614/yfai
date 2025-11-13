"""安全守卫模块

负责权限检查、审批流程和审计日志
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """风险等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    """审批状态"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ApprovalRequest(BaseModel):
    """审批请求"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = Field(..., description="工具名称")
    tool_type: str = Field(..., description="工具类型")
    params: Dict[str, Any] = Field(..., description="参数")
    risk_level: RiskLevel = Field(..., description="风险等级")
    source: str = Field(default="user", description="来源")
    description: str = Field(default="", description="描述")
    impact: str = Field(default="", description="影响评估")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timeout_seconds: int = Field(default=60, description="超时时间(秒)")


class ApprovalResult(BaseModel):
    """审批结果"""

    request_id: str = Field(..., description="请求ID")
    status: ApprovalStatus = Field(..., description="审批状态")
    approved_by: Optional[str] = Field(None, description="审批人")
    reason: Optional[str] = Field(None, description="理由")
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class SecurityGuard:
    """安全守卫"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.confirm_threshold = self._parse_threshold(
            config.get("security", {}).get("confirm_threshold", "medium")
        )
        self.auto_audit = config.get("security", {}).get("auto_audit", True)
        self.redact_config = config.get("security", {}).get("redact", {})

        # 审批回调函数
        self.approval_callback: Optional[Callable[[ApprovalRequest], ApprovalResult]] = (
            None
        )

        # 审批记录
        self.approval_history: list[ApprovalResult] = []

    def _parse_threshold(self, threshold: str) -> RiskLevel:
        """解析确认阈值

        Args:
            threshold: 阈值字符串

        Returns:
            RiskLevel: 风险等级
        """
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        return mapping.get(threshold, RiskLevel.MEDIUM)

    def set_approval_callback(
        self, callback: Callable[[ApprovalRequest], ApprovalResult]
    ) -> None:
        """设置审批回调函数

        Args:
            callback: 回调函数
        """
        self.approval_callback = callback

    def check_permission(
        self,
        tool_name: str,
        tool_type: str,
        params: Dict[str, Any],
        risk_level: str = "medium",
    ) -> bool:
        """检查权限

        Args:
            tool_name: 工具名称
            tool_type: 工具类型
            params: 参数
            risk_level: 风险等级

        Returns:
            bool: 是否允许
        """
        # 解析风险等级
        try:
            risk = RiskLevel(risk_level)
        except ValueError:
            risk = RiskLevel.MEDIUM

        # 检查是否需要审批
        if self._needs_approval(risk):
            return False

        # 低于阈值的操作自动允许
        return True

    def _needs_approval(self, risk_level: RiskLevel) -> bool:
        """判断是否需要审批

        Args:
            risk_level: 风险等级

        Returns:
            bool: 是否需要审批
        """
        risk_values = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }

        return risk_values[risk_level] >= risk_values[self.confirm_threshold]

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        """请求审批

        Args:
            request: 审批请求

        Returns:
            ApprovalResult: 审批结果
        """
        # 如果设置了回调函数,调用它
        if self.approval_callback:
            result = self.approval_callback(request)
        else:
            # 默认拒绝
            result = ApprovalResult(
                request_id=request.id,
                status=ApprovalStatus.REJECTED,
                reason="未设置审批回调函数",
            )

        # 记录审批结果
        self.approval_history.append(result)

        # 审计日志
        if self.auto_audit:
            self._audit_log(request, result)

        return result

    def _audit_log(self, request: ApprovalRequest, result: ApprovalResult) -> None:
        """审计日志

        Args:
            request: 审批请求
            result: 审批结果
        """
        # TODO: 写入数据库
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request.id,
            "tool_name": request.tool_name,
            "tool_type": request.tool_type,
            "risk_level": request.risk_level,
            "status": result.status,
            "approved_by": result.approved_by,
            "reason": result.reason,
        }
        print(f"[AUDIT] {log_entry}")

    def redact_sensitive_info(self, text: str) -> str:
        """脱敏敏感信息

        Args:
            text: 原始文本

        Returns:
            str: 脱敏后的文本
        """
        redacted = text

        # 脱敏路径
        paths = self.redact_config.get("paths", [])
        for path in paths:
            # 简单替换,实际应该使用正则
            redacted = redacted.replace(path, "***REDACTED_PATH***")

        # 脱敏环境变量
        envs = self.redact_config.get("envs", [])
        for env_pattern in envs:
            # 简单检查,实际应该使用正则匹配
            if env_pattern in redacted:
                redacted = redacted.replace(env_pattern, "***REDACTED_ENV***")

        return redacted

    def get_approval_stats(self) -> Dict[str, Any]:
        """获取审批统计

        Returns:
            Dict[str, Any]: 统计信息
        """
        total = len(self.approval_history)
        approved = sum(
            1 for r in self.approval_history if r.status == ApprovalStatus.APPROVED
        )
        rejected = sum(
            1 for r in self.approval_history if r.status == ApprovalStatus.REJECTED
        )
        timeout = sum(
            1 for r in self.approval_history if r.status == ApprovalStatus.TIMEOUT
        )

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "timeout": timeout,
            "approval_rate": approved / total if total > 0 else 0,
        }

