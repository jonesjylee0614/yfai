"""设置对话框"""

from typing import Any, Dict

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QHBoxLayout,
    QFormLayout,
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.config = config
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("设置")
        self.resize(600, 500)

        layout = QVBoxLayout()

        # 标签页
        tabs = QTabWidget()

        # 通用设置
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "通用")

        # Provider设置
        provider_tab = self._create_provider_tab()
        tabs.addTab(provider_tab, "模型提供商")

        # 安全设置
        security_tab = self._create_security_tab()
        tabs.addTab(security_tab, "安全")

        layout.addWidget(tabs)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_general_tab(self) -> QWidget:
        """创建通用设置标签页"""
        widget = QWidget()
        layout = QFormLayout()

        # 自动保存
        auto_save_check = QCheckBox()
        auto_save_check.setChecked(self.config.get("app", {}).get("auto_save", True))
        layout.addRow("自动保存会话:", auto_save_check)

        # 流式输出
        stream_check = QCheckBox()
        stream_check.setChecked(
            self.config.get("app", {}).get("stream_output", True)
        )
        layout.addRow("流式输出:", stream_check)

        # 超时设置
        timeout_spin = QSpinBox()
        timeout_spin.setRange(10, 300)
        timeout_spin.setValue(self.config.get("app", {}).get("timeout_sec", 60))
        layout.addRow("超时时间(秒):", timeout_spin)

        widget.setLayout(layout)
        return widget

    def _create_provider_tab(self) -> QWidget:
        """创建Provider设置标签页"""
        widget = QWidget()
        layout = QFormLayout()

        # 百炼API Key
        bailian_key = QLineEdit()
        bailian_key.setPlaceholderText("输入百炼API Key")
        bailian_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("百炼API Key:", bailian_key)

        # Ollama地址
        ollama_base = QLineEdit()
        ollama_base.setText(
            self.config.get("providers", {})
            .get("ollama", {})
            .get("api_base", "http://127.0.0.1:11434")
        )
        layout.addRow("Ollama地址:", ollama_base)

        widget.setLayout(layout)
        return widget

    def _create_security_tab(self) -> QWidget:
        """创建安全设置标签页"""
        widget = QWidget()
        layout = QFormLayout()

        # 自动审计
        auto_audit = QCheckBox()
        auto_audit.setChecked(
            self.config.get("security", {}).get("auto_audit", True)
        )
        layout.addRow("自动审计:", auto_audit)

        # 日志保留天数
        log_retention = QSpinBox()
        log_retention.setRange(1, 365)
        log_retention.setValue(
            self.config.get("security", {}).get("log_retention_days", 30)
        )
        layout.addRow("日志保留天数:", log_retention)

        widget.setLayout(layout)
        return widget

