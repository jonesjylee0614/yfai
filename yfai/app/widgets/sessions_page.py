"""会话管理页面"""

from datetime import datetime, timedelta

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
    QTextEdit,
    QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import Qt

from sqlalchemy import func


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
            "标题", "助手/知识库", "消息数", "最后活动", "操作", "ID"
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

    def _load_sessions(self):
        """加载会话列表"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Session, Message

                sessions = (
                    db_session.query(Session)
                    .order_by(Session.created_at.desc())
                    .limit(100)
                    .all()
                )

                stats_map = self._collect_message_stats(db_session)
                self.table.setRowCount(len(sessions))

                for row, session in enumerate(sessions):
                    # 标题
                    self.table.setItem(row, 0, QTableWidgetItem(session.title))

                    # 关联信息
                    assistant_name = session.assistant.name if session.assistant else "-"
                    kb_name = session.knowledge_base.name if session.knowledge_base else "-"
                    context_parts = [name for name in [assistant_name, kb_name] if name != "-"]
                    context_text = " | ".join(context_parts) if context_parts else "-"
                    self.table.setItem(row, 1, QTableWidgetItem(context_text))

                    # 消息统计
                    stats = stats_map.get(session.id, {})
                    msg_count = stats.get("count", 0)
                    self.table.setItem(row, 2, QTableWidgetItem(str(msg_count)))

                    # 最后活动
                    last_active = stats.get("last") or session.updated_at or session.created_at
                    last_str = last_active.strftime("%Y-%m-%d %H:%M") if last_active else "-"
                    self.table.setItem(row, 3, QTableWidgetItem(last_str))

                    # 操作按钮
                    actions_widget = self._create_action_buttons(session.id)
                    self.table.setCellWidget(row, 4, actions_widget)

                    # ID (隐藏)
                    self.table.setItem(row, 5, QTableWidgetItem(session.id))

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载会话列表失败: {e}")

    def _collect_message_stats(self, db_session):
        """汇总每个会话的消息统计"""
        from yfai.store.db import Message

        stats_rows = (
            db_session.query(
                Message.session_id.label("session_id"),
                func.count(Message.id).label("count"),
                func.max(Message.created_at).label("last"),
            )
            .group_by(Message.session_id)
            .all()
        )
        return {row.session_id: {"count": row.count, "last": row.last} for row in stats_rows}

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
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Session, Message

                session = db_session.query(Session).filter_by(id=session_id).first()
                if not session:
                    QMessageBox.warning(self, "提示", "未找到该会话")
                    return

                messages = (
                    db_session.query(Message)
                    .filter(Message.session_id == session_id)
                    .order_by(Message.created_at)
                    .all()
                )

                session_info = {
                    "title": session.title,
                    "assistant": session.assistant.name if session.assistant else None,
                    "knowledge": session.knowledge_base.name if session.knowledge_base else None,
                }
                messages_data = [
                    {
                        "role": message.role,
                        "content": message.content,
                        "created_at": message.created_at,
                    }
                    for message in messages
                ]

                dialog = SessionDetailsDialog(session_info, messages_data, parent=self)
                dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载会话详情失败: {e}")

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
        cutoff_days = 30
        reply = QMessageBox.question(
            self,
            "确认清理",
            f"将删除{cutoff_days}天未活跃的会话，是否继续?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        cutoff_time = datetime.utcnow() - timedelta(days=cutoff_days)
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Session

                stats_map = self._collect_message_stats(db_session)
                sessions = db_session.query(Session).all()
                removed = 0

                for session in sessions:
                    last_active = stats_map.get(session.id, {}).get(
                        "last", session.created_at
                    )
                    if not last_active or last_active < cutoff_time:
                        db_session.delete(session)
                        removed += 1

                db_session.commit()

            QMessageBox.information(self, "完成", f"已清理 {removed} 个会话")
            self._load_sessions()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"清理会话失败: {e}")


class SessionDetailsDialog(QDialog):
    """会话详情对话框"""

    def __init__(self, session_info, messages, parent=None):
        super().__init__(parent)
        self.session_info = session_info
        self.messages = messages
        self.setWindowTitle("会话详情")
        self.resize(600, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        meta_text = f"<b>标题:</b> {self.session_info.get('title', '-')}"
        assistant_name = self.session_info.get("assistant")
        knowledge_name = self.session_info.get("knowledge")
        if assistant_name:
            meta_text += f" | <b>助手:</b> {assistant_name}"
        if knowledge_name:
            meta_text += f" | <b>知识库:</b> {knowledge_name}"
        meta_label = QLabel(meta_text)
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)

        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)
        self.messages_view.setPlaceholderText("暂无消息")
        layout.addWidget(self.messages_view)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._render_messages()

    def _render_messages(self):
        if not self.messages:
            self.messages_view.setPlainText("暂无消息")
            return

        lines = []
        for message in self.messages:
            timestamp = (
                message["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                if message["created_at"]
                else "--"
            )
            role = message["role"].upper()
            lines.append(f"[{timestamp}] {role}")
            lines.append(message["content"])
            lines.append("")

        self.messages_view.setPlainText("\n".join(lines).strip())
