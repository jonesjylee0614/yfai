"""审批对话框组件"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from yfai.security.guard import ApprovalRequest, RiskLevel


class ApprovalDialog(QDialog):
    """审批对话框

    用于显示工具执行审批请求，让用户决定是否允许执行
    """

    # 审批结果常量
    REJECTED = 0
    APPROVED_ONCE = 1
    APPROVED_ALWAYS = 2

    def __init__(self, request: ApprovalRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.result = self.REJECTED  # 默认拒绝

        self.setWindowTitle("安全审批请求")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 风险等级提示
        risk_frame = self._create_risk_frame()
        layout.addWidget(risk_frame)

        # 工具信息
        info_frame = self._create_info_frame()
        layout.addWidget(info_frame)

        # 参数详情
        params_label = QLabel("执行参数:")
        params_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(params_label)

        self.params_text = QTextEdit()
        self.params_text.setReadOnly(True)
        self.params_text.setMaximumHeight(150)
        params_str = self._format_params(self.request.params)
        self.params_text.setPlainText(params_str)
        layout.addWidget(self.params_text)

        # 影响评估（如果有）
        if self.request.impact:
            impact_label = QLabel("影响评估:")
            impact_label.setStyleSheet("font-weight: bold; color: #d63031;")
            layout.addWidget(impact_label)

            impact_text = QLabel(self.request.impact)
            impact_text.setWordWrap(True)
            impact_text.setStyleSheet("padding: 10px; background-color: #fff5f5; border-left: 3px solid #d63031;")
            layout.addWidget(impact_text)

        layout.addStretch()

        # 按钮区域
        buttons_layout = self._create_buttons()
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _create_risk_frame(self) -> QFrame:
        """创建风险等级提示框"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)

        # 根据风险等级设置颜色
        risk_colors = {
            RiskLevel.LOW: ("#00b894", "#e8f8f5"),
            RiskLevel.MEDIUM: ("#fdcb6e", "#fff9e6"),
            RiskLevel.HIGH: ("#e17055", "#fff0ed"),
            RiskLevel.CRITICAL: ("#d63031", "#fff5f5"),
        }
        border_color, bg_color = risk_colors.get(
            self.request.risk_level, ("#fdcb6e", "#fff9e6")
        )

        frame.setStyleSheet(
            f"QFrame {{ background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 10px; }}"
        )

        layout = QHBoxLayout(frame)

        # 风险图标
        risk_icons = {
            RiskLevel.LOW: "ℹ️",
            RiskLevel.MEDIUM: "⚠️",
            RiskLevel.HIGH: "⚠️",
            RiskLevel.CRITICAL: "🚨",
        }
        icon = risk_icons.get(self.request.risk_level, "⚠️")

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24pt;")
        layout.addWidget(icon_label)

        # 风险信息
        risk_text_layout = QVBoxLayout()

        risk_level_label = QLabel(f"风险等级: {self.request.risk_level.value.upper()}")
        risk_level_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        risk_text_layout.addWidget(risk_level_label)

        if self.request.description:
            desc_label = QLabel(self.request.description)
            desc_label.setWordWrap(True)
            risk_text_layout.addWidget(desc_label)

        layout.addLayout(risk_text_layout)
        layout.addStretch()

        return frame

    def _create_info_frame(self) -> QFrame:
        """创建工具信息框"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(5)

        # 工具名称
        tool_name_layout = QHBoxLayout()
        tool_name_layout.addWidget(QLabel("<b>工具名称:</b>"))
        tool_name_layout.addWidget(QLabel(self.request.tool_name))
        tool_name_layout.addStretch()
        layout.addLayout(tool_name_layout)

        # 工具类型
        tool_type_layout = QHBoxLayout()
        tool_type_layout.addWidget(QLabel("<b>工具类型:</b>"))
        tool_type_layout.addWidget(QLabel(self.request.tool_type))
        tool_type_layout.addStretch()
        layout.addLayout(tool_type_layout)

        # 来源
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("<b>请求来源:</b>"))
        source_layout.addWidget(QLabel(self.request.source))
        source_layout.addStretch()
        layout.addLayout(source_layout)

        # 时间
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("<b>请求时间:</b>"))
        time_layout.addWidget(QLabel(self.request.created_at.strftime("%Y-%m-%d %H:%M:%S")))
        time_layout.addStretch()
        layout.addLayout(time_layout)

        return frame

    def _format_params(self, params: dict) -> str:
        """格式化参数字典"""
        if not params:
            return "(无参数)"

        lines = []
        for key, value in params.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _create_buttons(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()

        # 拒绝按钮
        reject_btn = QPushButton("🚫 拒绝")
        reject_btn.setStyleSheet(
            "QPushButton { background-color: #d63031; color: white; padding: 8px 16px; font-size: 12pt; } "
            "QPushButton:hover { background-color: #c0392b; }"
        )
        reject_btn.clicked.connect(lambda: self._on_decision(self.REJECTED))
        layout.addWidget(reject_btn)

        layout.addStretch()

        # 仅此一次允许按钮
        approve_once_btn = QPushButton("✓ 仅此一次允许")
        approve_once_btn.setStyleSheet(
            "QPushButton { background-color: #0984e3; color: white; padding: 8px 16px; font-size: 12pt; } "
            "QPushButton:hover { background-color: #0770c4; }"
        )
        approve_once_btn.clicked.connect(lambda: self._on_decision(self.APPROVED_ONCE))
        layout.addWidget(approve_once_btn)

        # 永久允许按钮（只在非 CRITICAL 风险时显示）
        if self.request.risk_level != RiskLevel.CRITICAL:
            approve_always_btn = QPushButton("✓✓ 永久允许")
            approve_always_btn.setStyleSheet(
                "QPushButton { background-color: #00b894; color: white; padding: 8px 16px; font-size: 12pt; } "
                "QPushButton:hover { background-color: #00a085; }"
            )
            approve_always_btn.clicked.connect(
                lambda: self._on_decision(self.APPROVED_ALWAYS)
            )
            layout.addWidget(approve_always_btn)

        return layout

    def _on_decision(self, decision: int):
        """处理决策"""
        self.result = decision
        self.accept()

    def get_result(self) -> int:
        """获取审批结果

        Returns:
            int: REJECTED(0), APPROVED_ONCE(1), 或 APPROVED_ALWAYS(2)
        """
        return self.result


def show_approval_dialog(request: ApprovalRequest, parent=None) -> int:
    """显示审批对话框的便捷函数

    Args:
        request: 审批请求
        parent: 父窗口

    Returns:
        int: 审批结果 (REJECTED=0, APPROVED_ONCE=1, APPROVED_ALWAYS=2)
    """
    dialog = ApprovalDialog(request, parent)
    dialog.exec()
    return dialog.get_result()
