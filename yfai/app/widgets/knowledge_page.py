"""知识库管理页面"""

import json
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
    QComboBox,
    QSpinBox,
)
from PyQt6.QtCore import Qt


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

        # 数据源类型
        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(["documents", "directory", "web", "database"])
        self.source_type_combo.currentTextChanged.connect(self._on_source_type_changed)
        form_layout.addRow("数据源类型:", self.source_type_combo)

        # 数据源路径/地址
        self.source_location_edit = QLineEdit()
        self.source_location_edit.setPlaceholderText("例如: ./docs 或 https://example.com")
        form_layout.addRow("路径/地址:", self.source_location_edit)

        # 高级配置
        self.config_edit = QTextEdit()
        self.config_edit.setPlaceholderText('{"include": ["*.md"]}')
        self.config_edit.setMaximumHeight(80)
        form_layout.addRow("额外配置(JSON):", self.config_edit)

        # 嵌入模型
        self.embedding_model_edit = QLineEdit()
        self.embedding_model_edit.setPlaceholderText("text-embedding-v1")
        form_layout.addRow("嵌入模型:", self.embedding_model_edit)

        # 分块策略
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 4000)
        self.chunk_size_spin.setValue(500)
        self.chunk_size_spin.setSuffix(" 字符")
        form_layout.addRow("分块大小:", self.chunk_size_spin)

        self.chunk_overlap_spin = QSpinBox()
        self.chunk_overlap_spin.setRange(0, 1000)
        self.chunk_overlap_spin.setValue(50)
        self.chunk_overlap_spin.setSuffix(" 字符")
        form_layout.addRow("块重叠:", self.chunk_overlap_spin)

        layout.addLayout(form_layout)

        # 按钮
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def _on_source_type_changed(self, source_type: str):
        """根据类型调整占位提示"""
        placeholders = {
            "documents": "例如: ./docs/guide.md 或 data/*.md",
            "directory": "例如: ./workspace/project",
            "web": "例如: https://example.com/docs",
            "database": "例如: sqlite:///data.db",
        }
        self.source_location_edit.setPlaceholderText(placeholders.get(source_type, ""))

    def _load_kb_data(self):
        """加载知识库数据"""
        if not self.kb:
            return

        self.name_edit.setText(self.kb.get("name", ""))
        self.description_edit.setPlainText(self.kb.get("description", ""))
        self.embedding_model_edit.setText(self.kb.get("embedding_model", "text-embedding-v1"))
        self.source_type_combo.setCurrentText(self.kb.get("source_type", "documents"))

        config = self.kb.get("source_config") or {}
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                config = {}
        # 提取常用路径字段
        location = (
            config.get("path")
            or config.get("directory")
            or config.get("url")
            or config.get("connection")
            or ""
        )
        self.source_location_edit.setText(location)
        if config:
            self.config_edit.setPlainText(json.dumps(config, indent=2, ensure_ascii=False))

        self.chunk_size_spin.setValue(self.kb.get("chunk_size", 500) or 500)
        self.chunk_overlap_spin.setValue(self.kb.get("chunk_overlap", 50) or 50)

    def get_kb_data(self) -> dict:
        """获取知识库数据"""
        source_type = self.source_type_combo.currentText()
        location = self.source_location_edit.text().strip()

        config = {}
        if location:
            if source_type in ("documents", "directory"):
                config["path"] = location
            elif source_type == "web":
                config["url"] = location
            elif source_type == "database":
                config["connection"] = location

        extra = self.config_edit.toPlainText().strip()
        if extra:
            try:
                extra_config = json.loads(extra)
                config.update(extra_config)
            except json.JSONDecodeError:
                pass

        return {
            "name": self.name_edit.text(),
            "description": self.description_edit.toPlainText(),
            "source_type": source_type,
            "source_config": json.dumps(config, ensure_ascii=False),
            "embedding_model": self.embedding_model_edit.text() or "text-embedding-v1",
            "chunk_size": self.chunk_size_spin.value(),
            "chunk_overlap": self.chunk_overlap_spin.value(),
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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "名称", "数据源", "文档数", "嵌入模型", "最后索引", "操作", "ID"
        ])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnHidden(6, True)  # 隐藏ID列
        self.table.setAlternatingRowColors(True)

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

                    # 数据源类型
                    self.table.setItem(row, 1, QTableWidgetItem(kb.source_type))

                    # 文档数
                    chunk_count = kb.chunk_count or 0
                    self.table.setItem(row, 2, QTableWidgetItem(str(chunk_count)))

                    # 嵌入模型
                    self.table.setItem(row, 3, QTableWidgetItem(kb.embedding_model or "-"))

                    # 最后索引时间
                    last_indexed = kb.indexed_at.strftime("%Y-%m-%d %H:%M") if kb.indexed_at else "-"
                    self.table.setItem(row, 4, QTableWidgetItem(last_indexed))

                    # 操作按钮
                    actions_widget = self._create_action_buttons(kb.id)
                    self.table.setCellWidget(row, 5, actions_widget)

                    # ID (隐藏)
                    self.table.setItem(row, 6, QTableWidgetItem(kb.id))

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
