"""聊天组件"""

import asyncio
import uuid
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont


class MessageBubble(QWidget):
    """消息气泡"""

    def __init__(self, role: str, content: str, parent=None):
        super().__init__(parent)
        self.role = role
        self.content = content
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        # 创建消息标签
        message_label = QLabel(self.content)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # 根据角色设置样式
        if self.role == "user":
            message_label.setStyleSheet(
                """
                QLabel {
                    background-color: #1890ff;
                    color: white;
                    border-radius: 10px;
                    padding: 10px;
                    max-width: 600px;
                }
            """
            )
            layout.addStretch()
            layout.addWidget(message_label)
        else:
            message_label.setStyleSheet(
                """
                QLabel {
                    background-color: #f0f0f0;
                    color: #333;
                    border-radius: 10px;
                    padding: 10px;
                    max-width: 600px;
                }
            """
            )
            layout.addWidget(message_label)
            layout.addStretch()

        self.setLayout(layout)


class ChatWidget(QWidget):
    """聊天组件"""

    status_changed = pyqtSignal(str)

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.current_session_id: Optional[str] = None
        self.current_provider: Optional[str] = None

        self._init_ui()
        # 延迟到事件循环启动后再创建会话
        QTimer.singleShot(0, self.new_session)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 消息显示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()

        scroll_area.setWidget(self.messages_widget)
        layout.addWidget(scroll_area)

        # 输入区域
        input_layout = QHBoxLayout()

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入消息... (Shift+Enter 换行, Enter 发送)")
        self.input_text.setMaximumHeight(100)
        self.input_text.installEventFilter(self)
        input_layout.addWidget(self.input_text)

        self.send_btn = QPushButton("发送")
        self.send_btn.setMinimumWidth(80)
        self.send_btn.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        self.setLayout(layout)

    def eventFilter(self, obj, event):
        """事件过滤器"""
        if obj == self.input_text:
            from PyQt6.QtCore import QEvent
            from PyQt6.QtGui import QKeyEvent

            if event.type() == QEvent.Type.KeyPress:
                key_event: QKeyEvent = event
                if (
                    key_event.key() == Qt.Key.Key_Return
                    and not key_event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                ):
                    self._on_send_clicked()
                    return True

        return super().eventFilter(obj, event)

    def new_session(self):
        """新建会话"""
        async def create():
            self.current_session_id = await self.orchestrator.create_session()
            self.status_changed.emit("新建会话成功")

            # 清空消息显示
            while self.messages_layout.count() > 1:
                item = self.messages_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        asyncio.create_task(create())

    def _on_send_clicked(self):
        """发送按钮点击"""
        message = self.input_text.toPlainText().strip()
        if not message:
            return

        # 清空输入框
        self.input_text.clear()

        # 添加用户消息到UI
        self._add_message("user", message)

        # 发送消息
        self.send_btn.setEnabled(False)
        self.status_changed.emit("正在发送...")

        async def send():
            try:
                # 流式接收
                assistant_bubble = MessageBubble("assistant", "")
                # 在stretch之前插入
                self.messages_layout.insertWidget(
                    self.messages_layout.count() - 1, assistant_bubble
                )

                full_response = ""
                async for chunk in self.orchestrator.stream_chat(
                    message,
                    session_id=self.current_session_id,
                    provider=self.current_provider,
                ):
                    full_response += chunk
                    # 更新气泡内容
                    assistant_bubble.findChild(QLabel).setText(full_response)

                self.status_changed.emit("发送完成")

            except Exception as e:
                self.status_changed.emit(f"发送失败: {e}")
                self._add_message("assistant", f"错误: {e}")

            finally:
                self.send_btn.setEnabled(True)

        asyncio.create_task(send())

    def _add_message(self, role: str, content: str):
        """添加消息到UI"""
        bubble = MessageBubble(role, content)
        # 在stretch之前插入
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)

