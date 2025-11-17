"""聊天组件"""

import asyncio
import uuid
from typing import Optional, Tuple

import httpx
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QCheckBox,
    QComboBox,
    QSpinBox,
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
        self.current_model: Optional[str] = None
        self.current_assistant_id: Optional[str] = None
        self.current_assistant_name: Optional[str] = None
        self._display_provider_label = "默认"
        self._display_model_text = "默认"

        self._init_ui()
        # 延迟到事件循环启动后再创建会话
        QTimer.singleShot(0, self.new_session)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 当前助手状态
        status_layout = QHBoxLayout()
        self.assistant_label = QLabel("助手: 未选择")
        self.assistant_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.assistant_label)
        self.model_label = QLabel("模型: -")
        self.model_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.model_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

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

        # 扩展选项
        options_layout = QHBoxLayout()
        self.web_search_check = QCheckBox("联网查询")
        options_layout.addWidget(self.web_search_check)
        self.web_search_provider = QComboBox()
        self.web_search_provider.addItems(["DuckDuckGo", "Brave"])
        options_layout.addWidget(self.web_search_provider)
        options_layout.addWidget(QLabel("TopK"))
        self.web_search_top_k = QSpinBox()
        self.web_search_top_k.setRange(1, 10)
        self.web_search_top_k.setValue(3)
        options_layout.addWidget(self.web_search_top_k)
        options_layout.addWidget(QLabel("语言"))
        self.web_search_lang = QComboBox()
        self.web_search_lang.addItems(["auto", "zh-CN", "en-US"])
        options_layout.addWidget(self.web_search_lang)
        options_layout.addStretch()
        layout.addLayout(options_layout)

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
            title = "新对话"
            if self.current_assistant_name:
                title = f"{self.current_assistant_name} 对话"
            self.current_session_id = await self.orchestrator.create_session(
                title=title,
                assistant_id=self.current_assistant_id,
            )
            if self.current_assistant_name:
                self.status_changed.emit(f"新建会话（助手: {self.current_assistant_name}）")
            else:
                self.status_changed.emit("新建会话成功")

            self._reset_messages()

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
                web_context = None
                if self.web_search_check.isChecked():
                    self.status_changed.emit("正在联网搜索...")
                    web_context = await self._perform_web_search(message)

                async for chunk in self.orchestrator.stream_chat(
                    message,
                    session_id=self.current_session_id,
                    provider=self.current_provider,
                    model=self.current_model,
                    context=web_context,
                ):
                    full_response += chunk
                    # 更新气泡内容
                    assistant_bubble.findChild(QLabel).setText(full_response)

                meta = await self.orchestrator.get_last_assistant_metadata(self.current_session_id)
                if meta:
                    resolved_label = self._format_provider_label(meta.get("provider"))
                    resolved_model = meta.get("model") or "默认"
                    self.set_active_model(
                        self._display_provider_label,
                        self._display_model_text,
                        resolved=(resolved_label, resolved_model),
                    )
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

    def set_active_assistant(self, assistant: Optional[dict]) -> None:
        """设置当前助手"""
        if assistant:
            self.current_assistant_id = assistant.get("id")
            self.current_assistant_name = assistant.get("name")
            name = assistant.get("name") or "未命名助手"
            subtitle = assistant.get("description") or ""
            if subtitle:
                self.assistant_label.setText(f"助手: {name}｜{subtitle}")
            else:
                self.assistant_label.setText(f"助手: {name}")
        else:
            self.current_assistant_id = None
            self.current_assistant_name = None
            self.assistant_label.setText("助手: 未选择")

    def set_active_model(
        self,
        provider_label: Optional[str],
        model_name: Optional[str],
        resolved: Optional[Tuple[str, str]] = None,
    ) -> None:
        """展示当前 Provider/模型"""
        self._display_provider_label = provider_label or "默认"
        self._display_model_text = model_name or "默认"
        text = f"模型: {self._display_provider_label}/{self._display_model_text}"
        if resolved:
            resolved_provider, resolved_model = resolved
            if resolved_provider and resolved_model:
                resolved_text = f"{resolved_provider}/{resolved_model}"
                selected_text = f"{self._display_provider_label}/{self._display_model_text}"
                if resolved_text != selected_text:
                    text += f" → {resolved_text}"
        self.model_label.setText(text)

    async def _perform_web_search(self, query: str) -> Optional[str]:
        """联网搜索，返回摘要"""
        api = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(api, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            self.status_changed.emit(f"联网查询失败: {exc}")
            return None

        pieces = []
        abstract = data.get("AbstractText")
        if abstract:
            pieces.append(abstract.strip())

        related = data.get("RelatedTopics") or []
        for topic in related[:3]:
            if isinstance(topic, dict):
                text = topic.get("Text")
                url = topic.get("FirstURL")
                if text:
                    snippet = text if len(text) < 200 else text[:200] + "..."
                    if url:
                        pieces.append(f"{snippet} ({url})")
                    else:
                        pieces.append(snippet)

        summary = "\n".join(pieces).strip()
        if not summary:
            summary = "未从开放接口获得有效的联网结果。"
        return f"以下是联网检索到的参考信息：\n{summary}"

    def load_session(
        self,
        session_id: str,
        messages: list[dict],
        assistant: Optional[dict] = None,
    ) -> None:
        """加载历史会话到聊天窗口"""
        self.current_session_id = session_id
        if assistant:
            self.set_active_assistant(assistant)

        self._reset_messages()
        for msg in messages:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            self._add_message(role, content)

        self.status_changed.emit("已加载历史会话")

    def _reset_messages(self) -> None:
        """清空消息列表"""
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _format_provider_label(self, provider_key: Optional[str]) -> str:
        mapping = {
            "bailian": "百炼(DashScope)",
            "ollama": "Ollama",
            "auto": "自动",
            None: "默认",
        }
        return mapping.get(provider_key, provider_key or "默认")

