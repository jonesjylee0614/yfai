"""助手管理页面"""

import uuid
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class AssistantDialog(QDialog):
    """助手编辑对话框"""

    def __init__(self, orchestrator, assistant: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.assistant = assistant
        self.is_edit = assistant is not None

        self.setWindowTitle("编辑助手" if self.is_edit else "创建助手")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._init_ui()
        if self.is_edit:
            self._load_assistant_data()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 表单
        form_layout = QFormLayout()

        # 助手名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("助手名称")
        form_layout.addRow("名称:", self.name_edit)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("助手描述")
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow("描述:", self.description_edit)

        # 系统提示词
        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setPlaceholderText("你是一个有帮助的AI助手...")
        self.system_prompt_edit.setMinimumHeight(150)
        form_layout.addRow("系统提示词:", self.system_prompt_edit)

        # 默认Provider
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["bailian", "ollama"])
        form_layout.addRow("默认Provider:", self.provider_combo)

        # 默认Model
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("qwen-plus")
        form_layout.addRow("默认模型:", self.model_edit)

        # 是否内置
        self.builtin_check = QCheckBox()
        form_layout.addRow("内置助手:", self.builtin_check)

        layout.addLayout(form_layout)

        # 按钮
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def _load_assistant_data(self):
        """加载助手数据"""
        if not self.assistant:
            return

        self.name_edit.setText(self.assistant.get("name", ""))
        self.description_edit.setPlainText(self.assistant.get("description", ""))
        self.system_prompt_edit.setPlainText(self.assistant.get("system_prompt", ""))
        self.provider_combo.setCurrentText(self.assistant.get("provider", "bailian"))
        self.model_edit.setText(self.assistant.get("model", ""))
        self.builtin_check.setChecked(self.assistant.get("is_builtin", False))

    def get_assistant_data(self) -> dict:
        """获取助手数据"""
        return {
            "name": self.name_edit.text(),
            "description": self.description_edit.toPlainText(),
            "system_prompt": self.system_prompt_edit.toPlainText(),
            "provider": self.provider_combo.currentText(),
            "model": self.model_edit.text(),
            "is_builtin": self.builtin_check.isChecked(),
        }


class AssistantsPage(QWidget):
    """助手管理页面"""

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_assistants()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 顶部工具栏
        toolbar = QHBoxLayout()

        create_btn = QPushButton("➕ 创建助手")
        create_btn.clicked.connect(self._create_assistant)
        toolbar.addWidget(create_btn)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_assistants)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 助手列表
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "名称", "Provider/模型", "内置", "创建时间", "操作", "ID"
        ])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnHidden(5, True)  # 隐藏ID列
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _load_assistants(self):
        """加载助手列表"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Assistant

                assistants = db_session.query(Assistant).all()
                self.table.setRowCount(len(assistants))

                for row, assistant in enumerate(assistants):
                    # 名称
                    self.table.setItem(row, 0, QTableWidgetItem(assistant.name))

                    # Provider/模型
                    provider = assistant.provider or "-"
                    model = assistant.model or "-"
                    provider_model = f"{provider}/{model}"
                    self.table.setItem(row, 1, QTableWidgetItem(provider_model))

                    # 内置
                    builtin_item = QTableWidgetItem("✓ 是" if assistant.is_builtin else "✗ 否")
                    if assistant.is_builtin:
                        builtin_item.setForeground(QColor("#0984e3"))
                    self.table.setItem(row, 2, builtin_item)

                    # 创建时间
                    created = assistant.created_at.strftime("%Y-%m-%d %H:%M")
                    self.table.setItem(row, 3, QTableWidgetItem(created))

                    # 操作按钮
                    actions_widget = self._create_action_buttons(assistant.id, assistant.is_builtin)
                    self.table.setCellWidget(row, 4, actions_widget)

                    # ID (隐藏)
                    self.table.setItem(row, 5, QTableWidgetItem(assistant.id))

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载助手列表失败: {e}")

    def _create_action_buttons(self, assistant_id: str, is_builtin: bool) -> QWidget:
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 编辑按钮
        edit_btn = QPushButton("✎")
        edit_btn.setMaximumWidth(30)
        edit_btn.setToolTip("编辑")
        edit_btn.clicked.connect(lambda: self._edit_assistant(assistant_id))
        layout.addWidget(edit_btn)

        # 删除按钮（内置助手不允许删除）
        if not is_builtin:
            delete_btn = QPushButton("🗑")
            delete_btn.setMaximumWidth(30)
            delete_btn.setToolTip("删除")
            delete_btn.clicked.connect(lambda: self._delete_assistant(assistant_id))
            layout.addWidget(delete_btn)

        return widget

    def _create_assistant(self):
        """创建助手"""
        dialog = AssistantDialog(self.orchestrator, parent=self)
        if dialog.exec():
            try:
                data = dialog.get_assistant_data()
                data["id"] = str(uuid.uuid4())

                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import Assistant

                    assistant = Assistant(**data)
                    db_session.add(assistant)
                    db_session.commit()

                QMessageBox.information(self, "成功", "助手创建成功")
                self._load_assistants()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建助手失败: {e}")

    def _edit_assistant(self, assistant_id: str):
        """编辑助手"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Assistant

                assistant = db_session.query(Assistant).filter_by(id=assistant_id).first()
                if not assistant:
                    QMessageBox.warning(self, "警告", "助手不存在")
                    return

                assistant_dict = assistant.to_dict()

            dialog = AssistantDialog(self.orchestrator, assistant_dict, parent=self)
            if dialog.exec():
                data = dialog.get_assistant_data()

                with self.orchestrator.db_manager.get_session() as db_session:
                    assistant = db_session.query(Assistant).filter_by(id=assistant_id).first()
                    if assistant:
                        for key, value in data.items():
                            setattr(assistant, key, value)
                        assistant.updated_at = datetime.utcnow()
                        db_session.commit()

                QMessageBox.information(self, "成功", "助手更新成功")
                self._load_assistants()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑助手失败: {e}")

    def _delete_assistant(self, assistant_id: str):
        """删除助手"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除此助手吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import Assistant

                    assistant = db_session.query(Assistant).filter_by(id=assistant_id).first()
                    if assistant:
                        db_session.delete(assistant)
                        db_session.commit()

                QMessageBox.information(self, "成功", "助手已删除")
                self._load_assistants()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除助手失败: {e}")
