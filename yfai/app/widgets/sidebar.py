"""侧边栏组件"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SidebarWidget(QWidget):
    """侧边栏组件"""

    page_changed = pyqtSignal(str)

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(5)

        # Logo/标题
        title_label = QLabel("YFAI")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 导航按钮
        nav_buttons = [
            ("💬 对话", "chat"),
            ("🤖 助手", "assistants"),
            ("🤵 智能体", "agents"),
            ("📚 会话", "sessions"),
            ("📊 运行记录", "jobs"),
            ("🔗 连接器", "connectors"),
            ("🤖 自动化", "automation"),
            ("📖 知识库", "knowledge"),
            ("🧠 模型", "models"),
            ("🔧 工具", "tools"),
            ("📋 日志", "logs"),
            ("⚙️ 设置", "settings"),
        ]

        for text, page_id in nav_buttons:
            btn = QPushButton(text)
            btn.setMinimumHeight(40)
            btn.setStyleSheet(
                """
                QPushButton {
                    text-align: left;
                    padding-left: 15px;
                    border: none;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """
            )
            btn.clicked.connect(lambda checked, p=page_id: self._on_nav_clicked(p))
            layout.addWidget(btn)

        layout.addStretch()

        # 版本信息
        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(version_label)

        self.setLayout(layout)
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)

        # 设置背景色
        self.setStyleSheet("QWidget { background-color: #2c2c2c; color: white; }")

    def _on_nav_clicked(self, page_id: str):
        """导航按钮点击"""
        self.page_changed.emit(page_id)

