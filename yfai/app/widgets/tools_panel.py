"""工具面板组件"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLineEdit,
)
from PyQt6.QtCore import Qt


class ToolsPanel(QWidget):
    """工具面板"""

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_tools()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title_label = QLabel("工具箱")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索工具...")
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input)

        # 工具列表
        self.tools_list = QListWidget()
        layout.addWidget(self.tools_list)

        self.setLayout(layout)
        self.setMinimumWidth(250)

    def _load_tools(self):
        """加载工具列表"""
        # 本地工具
        local_tools = [
            ("📁 文件读取", "fs.read", "low"),
            ("📝 文件写入", "fs.write", "medium"),
            ("📂 列出目录", "fs.list", "low"),
            ("🔍 搜索文件", "fs.search", "low"),
            ("🗑️ 删除文件", "fs.delete", "high"),
            ("⚡ 执行Shell", "shell.exec", "medium"),
            ("🔧 进程列表", "process.list", "low"),
            ("🌐 HTTP请求", "net.http", "low"),
        ]

        for name, tool_id, risk in local_tools:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, tool_id)

            # 根据风险等级设置颜色
            if risk == "low":
                item.setForeground(Qt.GlobalColor.green)
            elif risk == "medium":
                item.setForeground(Qt.GlobalColor.yellow)
            else:
                item.setForeground(Qt.GlobalColor.red)

            self.tools_list.addItem(item)

    def _on_search_changed(self, text: str):
        """搜索改变"""
        for i in range(self.tools_list.count()):
            item = self.tools_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

