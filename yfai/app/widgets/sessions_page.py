"""会话管理页面"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)
from PyQt6.QtCore import Qt


class SessionsPage(QWidget):
    """会话管理页面"""

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_sessions()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 顶部工具栏
        toolbar = QHBoxLayout()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_sessions)
        toolbar.addWidget(refresh_btn)

        clear_btn = QPushButton("🗑 清理旧会话")
        clear_btn.clicked.connect(self._clear_old_sessions)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 会话列表
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "标题", "消息数", "创建时间", "最后活动", "操作", "ID"
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

    def _load_sessions(self):
        """加载会话列表"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Session

                sessions = db_session.query(Session).order_by(Session.created_at.desc()).limit(100).all()
                self.table.setRowCount(len(sessions))

                for row, session in enumerate(sessions):
                    # 标题
                    self.table.setItem(row, 0, QTableWidgetItem(session.title))

                    # 消息数
                    self.table.setItem(row, 1, QTableWidgetItem(str(session.message_count)))

                    # 创建时间
                    created = session.created_at.strftime("%Y-%m-%d %H:%M")
                    self.table.setItem(row, 2, QTableWidgetItem(created))

                    # 最后活动
                    last_active = session.last_active_at.strftime("%Y-%m-%d %H:%M") if session.last_active_at else "-"
                    self.table.setItem(row, 3, QTableWidgetItem(last_active))

                    # 操作按钮
                    actions_widget = self._create_action_buttons(session.id)
                    self.table.setCellWidget(row, 4, actions_widget)

                    # ID (隐藏)
                    self.table.setItem(row, 5, QTableWidgetItem(session.id))

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载会话列表失败: {e}")

    def _create_action_buttons(self, session_id: str) -> QWidget:
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 查看按钮
        view_btn = QPushButton("👁")
        view_btn.setMaximumWidth(30)
        view_btn.setToolTip("查看消息")
        view_btn.clicked.connect(lambda: self._view_session(session_id))
        layout.addWidget(view_btn)

        # 删除按钮
        delete_btn = QPushButton("🗑")
        delete_btn.setMaximumWidth(30)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda: self._delete_session(session_id))
        layout.addWidget(delete_btn)

        return widget

    def _view_session(self, session_id: str):
        """查看会话"""
        # TODO: 实现会话详情查看
        QMessageBox.information(self, "提示", f"会话查看功能待实现\n会话ID: {session_id}")

    def _delete_session(self, session_id: str):
        """删除会话"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除此会话吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import Session

                    session = db_session.query(Session).filter_by(id=session_id).first()
                    if session:
                        db_session.delete(session)
                        db_session.commit()

                QMessageBox.information(self, "成功", "会话已删除")
                self._load_sessions()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除会话失败: {e}")

    def _clear_old_sessions(self):
        """清理旧会话"""
        # TODO: 实现清理逻辑，例如删除30天前的会话
        QMessageBox.information(self, "提示", "清理旧会话功能待实现")
