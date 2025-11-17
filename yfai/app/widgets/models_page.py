"""模型管理页面"""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
)


class ModelEditDialog(QDialog):
    """新增/编辑模型的对话框"""

    def __init__(
        self,
        provider_label: str,
        data: Optional[Dict[str, str]] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{provider_label} 模型")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("对话/写作/代码助手等")
        form.addRow("显示名称:", self.name_edit)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("qwen-plus / qwen2.5-coder 等")
        form.addRow("模型ID:", self.code_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("coding, general")
        form.addRow("标签(逗号分隔):", self.tags_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("用途说明或限制")
        self.desc_edit.setMaximumHeight(100)
        form.addRow("描述:", self.desc_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if data:
            self.name_edit.setText(data.get("name", ""))
            self.code_edit.setText(data.get("code", ""))
            tags = data.get("tags", [])
            if isinstance(tags, list):
                tags = ", ".join(tags)
            self.tags_edit.setText(tags or "")
            self.desc_edit.setPlainText(data.get("description", ""))

    def _on_accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写模型显示名称")
            return
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写模型ID")
            return
        self.accept()

    def get_data(self) -> Dict[str, str]:
        tags_str = self.tags_edit.text().strip()
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        return {
            "name": self.name_edit.text().strip(),
            "code": self.code_edit.text().strip(),
            "tags": tags,
            "description": self.desc_edit.toPlainText().strip(),
        }


class ModelsPage(QWidget):
    """模型与Provider配置管理页面"""

    config_updated = pyqtSignal(dict)

    def __init__(self, orchestrator, config_manager, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.config_manager = config_manager
        self.config = config_manager.get_all()
        self.current_provider = "bailian"
        self.provider_models: Dict[str, List[Dict[str, str]]] = {}

        self._init_ui()
        self._load_provider_config(self.current_provider)

    # UI ------------------------------------------------------------------
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🧠 模型与接口配置")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("维护各 Provider 的模型列表、API 接入信息与默认模型")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("选择 Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("百炼 (DashScope)", "bailian")
        self.provider_combo.addItem("Ollama", "ollama")
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self.provider_combo)
        provider_row.addStretch()
        layout.addLayout(provider_row)

        # 接口配置
        api_form = QFormLayout()
        self.api_base_edit = QLineEdit()
        api_form.addRow("API Base:", self.api_base_edit)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("API Key:", self.api_key_edit)

        self.default_model_edit = QLineEdit()
        api_form.addRow("默认模型:", self.default_model_edit)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setSuffix(" 秒")
        api_form.addRow("请求超时:", self.timeout_spin)
        layout.addLayout(api_form)

        # 模型列表
        table_header = QHBoxLayout()
        table_header.addWidget(QLabel("自定义模型列表"))
        table_header.addStretch()

        self.add_model_btn = QPushButton("添加模型")
        self.add_model_btn.clicked.connect(self._add_model)
        table_header.addWidget(self.add_model_btn)

        self.edit_model_btn = QPushButton("编辑选中")
        self.edit_model_btn.clicked.connect(self._edit_model)
        table_header.addWidget(self.edit_model_btn)

        self.remove_model_btn = QPushButton("删除选中")
        self.remove_model_btn.clicked.connect(self._remove_model)
        table_header.addWidget(self.remove_model_btn)

        layout.addLayout(table_header)

        self.model_table = QTableWidget()
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels(["显示名称", "模型ID", "标签", "描述"])
        header_view = self.model_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.model_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.model_table)

        # 操作区
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self._on_save)
        action_row.addWidget(self.save_btn)
        layout.addLayout(action_row)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

    # Provider & model helpers ---------------------------------------------
    def _on_provider_changed(self, index: int) -> None:
        provider = self.provider_combo.currentData()
        self._save_current_models()
        self.current_provider = provider
        self._load_provider_config(provider)

    def _load_provider_config(self, provider: str) -> None:
        cfg = self.config.get("providers", {}).get(provider, {})
        self.api_base_edit.setText(cfg.get("api_base", ""))
        self.api_key_edit.setText(cfg.get("api_key", ""))
        self.default_model_edit.setText(cfg.get("default_model", ""))
        self.timeout_spin.setValue(cfg.get("timeout", 60 if provider == "bailian" else 120))

        models = cfg.get("models", [])
        if not isinstance(models, list):
            models = []
        self.provider_models[provider] = models.copy()
        self._render_model_table(models)

    def _render_model_table(self, models: List[Dict[str, str]]) -> None:
        self.model_table.setRowCount(0)
        for model in models:
            self._append_model_row(model)

    def _append_model_row(self, data: Dict[str, str]) -> None:
        row = self.model_table.rowCount()
        self.model_table.insertRow(row)
        self.model_table.setItem(row, 0, QTableWidgetItem(data.get("name", "")))
        self.model_table.setItem(row, 1, QTableWidgetItem(data.get("code", "")))
        tags = data.get("tags", [])
        if isinstance(tags, list):
            tags_text = ", ".join(tags)
        else:
            tags_text = str(tags)
        self.model_table.setItem(row, 2, QTableWidgetItem(tags_text))
        self.model_table.setItem(row, 3, QTableWidgetItem(data.get("description", "")))

    def _selected_row(self) -> int:
        indexes = self.model_table.selectionModel().selectedRows()
        return indexes[0].row() if indexes else -1

    def _collect_models_from_table(self) -> List[Dict[str, str]]:
        models: List[Dict[str, str]] = []
        for row in range(self.model_table.rowCount()):
            name = self._item_text(row, 0)
            code = self._item_text(row, 1)
            tags_text = self._item_text(row, 2)
            desc = self._item_text(row, 3)
            if not code:
                continue
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            models.append(
                {
                    "name": name or code,
                    "code": code,
                    "tags": tags,
                    "description": desc,
                }
            )
        return models

    def _item_text(self, row: int, column: int) -> str:
        item = self.model_table.item(row, column)
        return item.text().strip() if item else ""

    def _save_current_models(self) -> None:
        if not self.current_provider:
            return
        self.provider_models[self.current_provider] = self._collect_models_from_table()

    # CRUD actions ---------------------------------------------------------
    def _add_model(self) -> None:
        label = self.provider_combo.currentText()
        dialog = ModelEditDialog(label, parent=self)
        if dialog.exec():
            self._append_model_row(dialog.get_data())

    def _edit_model(self) -> None:
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "提示", "请选择需要编辑的模型")
            return
        data = {
            "name": self._item_text(row, 0),
            "code": self._item_text(row, 1),
            "tags": [tag.strip() for tag in self._item_text(row, 2).split(",") if tag.strip()],
            "description": self._item_text(row, 3),
        }
        dialog = ModelEditDialog(self.provider_combo.currentText(), data, self)
        if dialog.exec():
            new_data = dialog.get_data()
            self.model_table.setItem(row, 0, QTableWidgetItem(new_data["name"]))
            self.model_table.setItem(row, 1, QTableWidgetItem(new_data["code"]))
            self.model_table.setItem(row, 2, QTableWidgetItem(", ".join(new_data.get("tags", []))))
            self.model_table.setItem(row, 3, QTableWidgetItem(new_data.get("description", "")))

    def _remove_model(self) -> None:
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "提示", "请选择需要删除的模型")
            return
        self.model_table.removeRow(row)

    # Save -----------------------------------------------------------------
    def _on_save(self) -> None:
        self._save_current_models()
        provider = self.current_provider
        models = self.provider_models.get(provider, [])

        self.config_manager.set(f"providers.{provider}.api_base", self.api_base_edit.text().strip())
        self.config_manager.set(f"providers.{provider}.api_key", self.api_key_edit.text().strip())
        self.config_manager.set(f"providers.{provider}.default_model", self.default_model_edit.text().strip())
        self.config_manager.set(f"providers.{provider}.timeout", self.timeout_spin.value())
        self.config_manager.set(f"providers.{provider}.models", models)
        self.config_manager.save()

        self.config = self.config_manager.get_all()
        self.status_label.setStyleSheet("color: #2ecc71;")
        self.status_label.setText("配置已保存")
        self.config_updated.emit(self.config)
