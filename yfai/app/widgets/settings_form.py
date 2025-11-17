"""Shared settings form widgets used by settings dialog/page."""

from __future__ import annotations

from typing import Any, Dict, List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QTreeWidget,
    QTreeWidgetItem,
)
from PyQt6.QtCore import Qt


class SettingsForm(QWidget):
    """Settings editor form shared by the dialog and page."""

    provider_options = [
        ("自动", "auto"),
        ("百炼(DashScope)", "bailian"),
        ("Ollama", "ollama"),
    ]

    def __init__(self, config: Dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config

        self._init_ui()
        self.load_config(config)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._create_general_tab()
        self._create_models_tab()
        self._create_provider_tab()
        self._create_security_tab()

    # General tab -----------------------------------------------------
    def _create_general_tab(self) -> None:
        widget = QWidget()
        form = QFormLayout(widget)

        self.default_provider_combo = QComboBox()
        for label, value in self.provider_options:
            if value == "auto":
                display = "自动路由"
            elif value == "bailian":
                display = "百炼(DashScope)"
            elif value == "ollama":
                display = "Ollama"
            else:
                display = label
            self.default_provider_combo.addItem(display, value)
        form.addRow("默认Provider:", self.default_provider_combo)

        self.auto_save_check = QCheckBox()
        form.addRow("自动保存会话:", self.auto_save_check)

        self.stream_check = QCheckBox()
        form.addRow("流式输出:", self.stream_check)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)
        self.timeout_spin.setSuffix(" 秒")
        form.addRow("超时时间:", self.timeout_spin)

        self.tool_decision_combo = QComboBox()
        self.tool_decision_combo.addItems([
            "rule_first_then_llm",
            "llm_only",
            "rule_only",
        ])
        form.addRow("工具决策模式:", self.tool_decision_combo)

        self.tabs.addTab(widget, "通用")

    # Model tab -------------------------------------------------------
    def _create_models_tab(self) -> None:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header = QLabel("配置任务到模型的路由, 并查看可用模型列表")
        header.setStyleSheet("color: #666;")
        layout.addWidget(header)

        table_layout = QHBoxLayout()
        table_label = QLabel("模型路由")
        table_layout.addWidget(table_label)
        table_layout.addStretch()

        self.add_route_btn = QPushButton("添加路由")
        self.remove_route_btn = QPushButton("删除选中")
        table_layout.addWidget(self.add_route_btn)
        table_layout.addWidget(self.remove_route_btn)
        layout.addLayout(table_layout)

        self.model_route_table = QTableWidget()
        self.model_route_table.setColumnCount(3)
        self.model_route_table.setHorizontalHeaderLabels(["任务类型", "Provider", "模型"])
        header_view = self.model_route_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.model_route_table)

        refresh_layout = QHBoxLayout()
        self.refresh_models_btn = QPushButton("刷新模型列表")
        self.models_status_label = QLabel("尚未加载")
        self.models_status_label.setStyleSheet("color: #888;")
        refresh_layout.addWidget(self.refresh_models_btn)
        refresh_layout.addWidget(self.models_status_label)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)

        self.models_tree = QTreeWidget()
        self.models_tree.setHeaderHidden(True)
        layout.addWidget(self.models_tree)

        self.tabs.addTab(widget, "模型")

        self.add_route_btn.clicked.connect(self._on_add_route)
        self.remove_route_btn.clicked.connect(self._remove_selected_route)

    # Provider tab ----------------------------------------------------
    def _create_provider_tab(self) -> None:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        bailian_group = QGroupBox("百炼 (DashScope)")
        bailian_form = QFormLayout(bailian_group)
        self.bailian_api_base = QLineEdit()
        bailian_form.addRow("API Base:", self.bailian_api_base)
        self.bailian_timeout = QSpinBox()
        self.bailian_timeout.setRange(5, 600)
        self.bailian_timeout.setSuffix(" 秒")
        bailian_form.addRow("超时时间:", self.bailian_timeout)
        self.bailian_retries = QSpinBox()
        self.bailian_retries.setRange(0, 10)
        bailian_form.addRow("最大重试:", self.bailian_retries)
        self.bailian_default_model = QLineEdit()
        bailian_form.addRow("默认模型:", self.bailian_default_model)
        self.bailian_key_env = QLineEdit()
        bailian_form.addRow("API Key 环境变量:", self.bailian_key_env)
        self.bailian_api_key = QLineEdit()
        self.bailian_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        bailian_form.addRow("API Key:", self.bailian_api_key)
        layout.addWidget(bailian_group)

        ollama_group = QGroupBox("Ollama")
        ollama_form = QFormLayout(ollama_group)
        self.ollama_api_base = QLineEdit()
        ollama_form.addRow("API Base:", self.ollama_api_base)
        self.ollama_timeout = QSpinBox()
        self.ollama_timeout.setRange(5, 600)
        self.ollama_timeout.setSuffix(" 秒")
        ollama_form.addRow("超时时间:", self.ollama_timeout)
        self.ollama_retries = QSpinBox()
        self.ollama_retries.setRange(0, 10)
        ollama_form.addRow("最大重试:", self.ollama_retries)
        self.ollama_default_model = QLineEdit()
        ollama_form.addRow("默认模型:", self.ollama_default_model)
        self.ollama_api_key = QLineEdit()
        self.ollama_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        ollama_form.addRow("访问令牌:", self.ollama_api_key)
        layout.addWidget(ollama_group)

        layout.addStretch()
        self.tabs.addTab(widget, "接口参数")

    # Security tab ----------------------------------------------------
    def _create_security_tab(self) -> None:
        widget = QWidget()
        form = QFormLayout(widget)

        self.confirm_combo = QComboBox()
        self.confirm_combo.addItems(["low", "medium", "high", "critical"])
        form.addRow("审批阈值:", self.confirm_combo)

        self.auto_audit_check = QCheckBox()
        form.addRow("自动审计:", self.auto_audit_check)

        self.log_retention_spin = QSpinBox()
        self.log_retention_spin.setRange(1, 365)
        self.log_retention_spin.setSuffix(" 天")
        form.addRow("日志保留时间:", self.log_retention_spin)

        self.tabs.addTab(widget, "安全")

    # Public API ------------------------------------------------------
    def load_config(self, config: Dict[str, Any]) -> None:
        """Populate fields from config."""

        self.config = config
        app_cfg = config.get("app", {})
        providers_cfg = config.get("providers", {})
        security_cfg = config.get("security", {})

        default_provider = app_cfg.get("default_provider", "bailian")
        idx = self.default_provider_combo.findData(default_provider)
        if idx >= 0:
            self.default_provider_combo.setCurrentIndex(idx)

        self.auto_save_check.setChecked(app_cfg.get("auto_save", True))
        self.stream_check.setChecked(app_cfg.get("stream_output", True))
        self.timeout_spin.setValue(app_cfg.get("timeout_sec", 60))
        tool_mode = app_cfg.get("tool_decision", "rule_first_then_llm")
        idx = self.tool_decision_combo.findText(tool_mode)
        if idx >= 0:
            self.tool_decision_combo.setCurrentIndex(idx)

        bailian_cfg = providers_cfg.get("bailian", {})
        self.bailian_api_base.setText(bailian_cfg.get("api_base", ""))
        self.bailian_timeout.setValue(bailian_cfg.get("timeout", 60))
        self.bailian_retries.setValue(bailian_cfg.get("max_retries", 3))
        self.bailian_default_model.setText(bailian_cfg.get("default_model", ""))
        self.bailian_key_env.setText(bailian_cfg.get("api_key_env", ""))
        self.bailian_api_key.setText(bailian_cfg.get("api_key", ""))

        ollama_cfg = providers_cfg.get("ollama", {})
        self.ollama_api_base.setText(ollama_cfg.get("api_base", ""))
        self.ollama_timeout.setValue(ollama_cfg.get("timeout", 120))
        self.ollama_retries.setValue(ollama_cfg.get("max_retries", 3))
        self.ollama_default_model.setText(ollama_cfg.get("default_model", ""))
        self.ollama_api_key.setText(ollama_cfg.get("api_key", ""))

        self.confirm_combo.setCurrentText(security_cfg.get("confirm_threshold", "medium"))
        self.auto_audit_check.setChecked(security_cfg.get("auto_audit", True))
        self.log_retention_spin.setValue(security_cfg.get("log_retention_days", 30))

        self._load_model_routes(app_cfg.get("model_route", {}))

    def collect_settings(self) -> Dict[str, Any]:
        """Return form values grouped by section."""

        app_cfg = {
            "default_provider": self.default_provider_combo.currentData(),
            "auto_save": self.auto_save_check.isChecked(),
            "stream_output": self.stream_check.isChecked(),
            "timeout_sec": self.timeout_spin.value(),
            "tool_decision": self.tool_decision_combo.currentText(),
            "model_route": self._collect_model_routes(),
        }

        providers_cfg = {
            "bailian": {
                "api_base": self.bailian_api_base.text().strip(),
                "timeout": self.bailian_timeout.value(),
                "max_retries": self.bailian_retries.value(),
                "default_model": self.bailian_default_model.text().strip(),
                "api_key_env": self.bailian_key_env.text().strip(),
                "api_key": self.bailian_api_key.text().strip(),
                "models": self.config.get("providers", {}).get("bailian", {}).get("models", []),
            },
            "ollama": {
                "api_base": self.ollama_api_base.text().strip(),
                "timeout": self.ollama_timeout.value(),
                "max_retries": self.ollama_retries.value(),
                "default_model": self.ollama_default_model.text().strip(),
                "api_key": self.ollama_api_key.text().strip(),
                "models": self.config.get("providers", {}).get("ollama", {}).get("models", []),
            },
        }

        security_cfg = {
            "confirm_threshold": self.confirm_combo.currentText(),
            "auto_audit": self.auto_audit_check.isChecked(),
            "log_retention_days": self.log_retention_spin.value(),
        }

        return {
            "app": app_cfg,
            "providers": providers_cfg,
            "security": security_cfg,
        }

    def set_available_models(self, models: Dict[str, List[str]]) -> None:
        """Populate available models tree."""

        self.models_tree.clear()
        total = 0
        for provider, items in models.items():
            provider_item = QTreeWidgetItem([provider])
            for model in sorted(items):
                QTreeWidgetItem(provider_item, [model])
                total += 1
            self.models_tree.addTopLevelItem(provider_item)
        self.models_tree.expandAll()

        if total:
            self.models_status_label.setText(f"已加载 {total} 个模型")
        else:
            self.models_status_label.setText("未获取到模型列表")

    # Helpers ---------------------------------------------------------
    def _load_model_routes(self, routes: Dict[str, str]) -> None:
        self.model_route_table.setRowCount(0)
        if not routes:
            self._add_route_row("general", "bailian", "qwen-plus")
            self._add_route_row("coding", "ollama", "qwen2.5-coder")
            return

        for task_type, route in routes.items():
            provider, model = self._split_route(route)
            self._add_route_row(task_type, provider, model)

    def _collect_model_routes(self) -> Dict[str, str]:
        routes: Dict[str, str] = {}
        for row in range(self.model_route_table.rowCount()):
            task_item = self.model_route_table.item(row, 0)
            provider_combo = self.model_route_table.cellWidget(row, 1)
            model_item = self.model_route_table.item(row, 2)

            task_type = task_item.text().strip() if task_item else ""
            provider = provider_combo.currentData() if provider_combo else None
            model = model_item.text().strip() if model_item else ""

            if not task_type:
                continue

            if provider and model:
                routes[task_type] = f"{provider}:{model}"
            elif provider:
                routes[task_type] = provider

        return routes

    def _add_route_row(self, task_type: str = "", provider: str | None = None, model: str = "") -> None:
        row = self.model_route_table.rowCount()
        self.model_route_table.insertRow(row)

        task_item = QTableWidgetItem(task_type)
        self.model_route_table.setItem(row, 0, task_item)

        provider_combo = QComboBox()
        for label, value in self.provider_options:
            provider_combo.addItem(label, value)
        if provider:
            idx = provider_combo.findData(provider)
            if idx >= 0:
                provider_combo.setCurrentIndex(idx)
        self.model_route_table.setCellWidget(row, 1, provider_combo)

        model_item = QTableWidgetItem(model)
        self.model_route_table.setItem(row, 2, model_item)

    def _remove_selected_route(self) -> None:
        selected = self.model_route_table.selectionModel().selectedRows()
        for index in sorted(selected, key=lambda i: i.row(), reverse=True):
            self.model_route_table.removeRow(index.row())

    def _on_add_route(self) -> None:
        self._add_route_row()

    @staticmethod
    def _split_route(route: str) -> tuple[str | None, str]:
        if ":" in route:
            provider, model = route.split(":", 1)
            return provider, model
        return route, ""
