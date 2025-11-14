"""知识库管理页面"""

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
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class KnowledgeBaseDialog(QDialog):
    """知识库编辑对话框"""

    def __init__(self, orchestrator, kb: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.kb = kb
        self.is_edit = kb is not None

        self.setWindowTitle("编辑知识库" if self.is_edit else "创建知识库")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._init_ui()
        if self.is_edit:
            self._load_kb_data()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 表单
        form_layout = QFormLayout()

        # 知识库名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("知识库名称")
        form_layout.addRow("名称:", self.name_edit)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("知识库描述")
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("描述:", self.description_edit)

        # 嵌入模型
        self.embedding_model_edit = QLineEdit()
        self.embedding_model_edit.setPlaceholderText("text-embedding-v1")
        form_layout.addRow("嵌入模型:", self.embedding_model_edit)

        # 向量维度
        self.dimension_edit = QLineEdit()
        self.dimension_edit.setPlaceholderText("1536")
        form_layout.addRow("向量维度:", self.dimension_edit)

        layout.addLayout(form_layout)

        # 按钮
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def _load_kb_data(self):
        """加载知识库数据"""
        if not self.kb:
            return

        self.name_edit.setText(self.kb.get("name", ""))
        self.description_edit.setPlainText(self.kb.get("description", ""))
        self.embedding_model_edit.setText(self.kb.get("embedding_model", ""))
        self.dimension_edit.setText(str(self.kb.get("dimension", "")))

    def get_kb_data(self) -> dict:
        """获取知识库数据"""
        return {
            "name": self.name_edit.text(),
            "description": self.description_edit.toPlainText(),
            "embedding_model": self.embedding_model_edit.text(),
            "dimension": int(self.dimension_edit.text() or "1536"),
        }


class KnowledgeBasePage(QWidget):
    """知识库管理页面"""

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_knowledge_bases()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 顶部工具栏
        toolbar = QHBoxLayout()

        create_btn = QPushButton("➕ 创建知识库")
        create_btn.clicked.connect(self._create_kb)
        toolbar.addWidget(create_btn)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_knowledge_bases)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 知识库列表
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "名称", "文档数", "向量维度", "最后更新", "操作", "ID"
        ])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnHidden(5, True)  # 隐藏ID列

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _load_knowledge_bases(self):
        """加载知识库列表"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import KnowledgeBase

                kbs = db_session.query(KnowledgeBase).all()
                self.table.setRowCount(len(kbs))

                for row, kb in enumerate(kbs):
                    # 名称
                    self.table.setItem(row, 0, QTableWidgetItem(kb.name))

                    # 文档数
                    self.table.setItem(row, 1, QTableWidgetItem(str(kb.document_count)))

                    # 向量维度
                    self.table.setItem(row, 2, QTableWidgetItem(str(kb.dimension)))

                    # 最后更新
                    last_update = kb.last_indexed_at.strftime("%Y-%m-%d %H:%M") if kb.last_indexed_at else "-"
                    self.table.setItem(row, 3, QTableWidgetItem(last_update))

                    # 操作按钮
                    actions_widget = self._create_action_buttons(kb.id)
                    self.table.setCellWidget(row, 4, actions_widget)

                    # ID (隐藏)
                    self.table.setItem(row, 5, QTableWidgetItem(kb.id))

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载知识库列表失败: {e}")

    def _create_action_buttons(self, kb_id: str) -> QWidget:
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 编辑按钮
        edit_btn = QPushButton("✎")
        edit_btn.setMaximumWidth(30)
        edit_btn.setToolTip("编辑")
        edit_btn.clicked.connect(lambda: self._edit_kb(kb_id))
        layout.addWidget(edit_btn)

        # 删除按钮
        delete_btn = QPushButton("🗑")
        delete_btn.setMaximumWidth(30)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda: self._delete_kb(kb_id))
        layout.addWidget(delete_btn)

        return widget

    def _create_kb(self):
        """创建知识库"""
        dialog = KnowledgeBaseDialog(self.orchestrator, parent=self)
        if dialog.exec():
            try:
                data = dialog.get_kb_data()
                data["id"] = str(uuid.uuid4())

                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import KnowledgeBase

                    kb = KnowledgeBase(**data)
                    db_session.add(kb)
                    db_session.commit()

                QMessageBox.information(self, "成功", "知识库创建成功")
                self._load_knowledge_bases()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建知识库失败: {e}")

    def _edit_kb(self, kb_id: str):
        """编辑知识库"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import KnowledgeBase

                kb = db_session.query(KnowledgeBase).filter_by(id=kb_id).first()
                if not kb:
                    QMessageBox.warning(self, "警告", "知识库不存在")
                    return

                kb_dict = kb.to_dict()

            dialog = KnowledgeBaseDialog(self.orchestrator, kb_dict, parent=self)
            if dialog.exec():
                data = dialog.get_kb_data()

                with self.orchestrator.db_manager.get_session() as db_session:
                    kb = db_session.query(KnowledgeBase).filter_by(id=kb_id).first()
                    if kb:
                        for key, value in data.items():
                            setattr(kb, key, value)
                        kb.updated_at = datetime.utcnow()
                        db_session.commit()

                QMessageBox.information(self, "成功", "知识库更新成功")
                self._load_knowledge_bases()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑知识库失败: {e}")

    def _delete_kb(self, kb_id: str):
        """删除知识库"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除此知识库吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import KnowledgeBase

                    kb = db_session.query(KnowledgeBase).filter_by(id=kb_id).first()
                    if kb:
                        db_session.delete(kb)
                        db_session.commit()

                QMessageBox.information(self, "成功", "知识库已删除")
                self._load_knowledge_bases()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除知识库失败: {e}")
