"""日志查看页面"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class LogsPage(QWidget):
    """日志查看页面"""

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_logs()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 顶部工具栏
        toolbar = QHBoxLayout()

        # 日志类型筛选
        toolbar.addWidget(QLabel("日志类型:"))
        self.log_type_combo = QComboBox()
        self.log_type_combo.addItems([
            "全部",
            "工具调用",
            "审批记录",
            "智能体运行",
            "系统事件",
        ])
        self.log_type_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.log_type_combo)

        # 日志级别筛选
        toolbar.addWidget(QLabel("级别:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["全部", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.log_level_combo)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_logs)
        toolbar.addWidget(refresh_btn)

        clear_btn = QPushButton("🗑 清空日志")
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 日志列表
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "时间", "类型", "级别", "消息", "详情"
        ])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _load_logs(self):
        """加载日志列表"""
        # TODO: 从数据库或日志文件加载实际的日志数据
        # 这里创建一些示例数据
        sample_logs = [
            {
                "timestamp": "2025-01-14 10:30:15",
                "type": "工具调用",
                "level": "INFO",
                "message": "执行文件读取操作: /home/user/test.txt",
                "details": "成功读取 1024 字节",
            },
            {
                "timestamp": "2025-01-14 10:29:45",
                "type": "审批记录",
                "level": "INFO",
                "message": "用户批准了文件删除操作",
                "details": "文件: /tmp/old_file.log",
            },
            {
                "timestamp": "2025-01-14 10:28:30",
                "type": "智能体运行",
                "level": "INFO",
                "message": "智能体 'DevOps助手' 完成任务",
                "details": "执行时间: 125ms, 状态: success",
            },
            {
                "timestamp": "2025-01-14 10:27:12",
                "type": "系统事件",
                "level": "WARNING",
                "message": "Provider 'ollama' 连接超时",
                "details": "尝试重连中...",
            },
        ]

        self.table.setRowCount(len(sample_logs))

        for row, log in enumerate(sample_logs):
            # 时间
            self.table.setItem(row, 0, QTableWidgetItem(log["timestamp"]))

            # 类型
            self.table.setItem(row, 1, QTableWidgetItem(log["type"]))

            # 级别
            level_item = QTableWidgetItem(log["level"])
            level_colors = {
                "INFO": "#0984e3",
                "WARNING": "#fdcb6e",
                "ERROR": "#d63031",
                "CRITICAL": "#a41623",
            }
            level_item.setForeground(QColor(level_colors.get(log["level"], "#000")))
            self.table.setItem(row, 2, level_item)

            # 消息
            self.table.setItem(row, 3, QTableWidgetItem(log["message"]))

            # 详情按钮
            details_widget = self._create_details_button(log["details"])
            self.table.setCellWidget(row, 4, details_widget)

    def _create_details_button(self, details: str) -> QWidget:
        """创建详情按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        details_btn = QPushButton("详情")
        details_btn.setMaximumWidth(60)
        details_btn.clicked.connect(lambda: self._show_details(details))
        layout.addWidget(details_btn)

        return widget

    def _show_details(self, details: str):
        """显示日志详情"""
        QMessageBox.information(self, "日志详情", details)

    def _on_filter_changed(self):
        """筛选条件改变"""
        # TODO: 根据筛选条件重新加载日志
        self._load_logs()

    def _clear_logs(self):
        """清空日志"""
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有日志吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # TODO: 实现清空日志的逻辑
            QMessageBox.information(self, "成功", "日志已清空")
            self._load_logs()
