"""运行记录页面"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QMessageBox,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json
from datetime import datetime


class JobsPage(QWidget):
    """运行记录页面"""

    job_selected = pyqtSignal(str)  # job_id

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.current_job_id = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("运行记录")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_jobs)
        title_layout.addWidget(refresh_btn)

        layout.addLayout(title_layout)

        # Job 列表
        self.job_list = QListWidget()
        self.job_list.itemClicked.connect(self._on_job_selected)
        self.job_list.itemDoubleClicked.connect(self._on_job_details)
        layout.addWidget(self.job_list)

        # 操作按钮
        action_layout = QHBoxLayout()
        details_btn = QPushButton("📋 查看详情")
        details_btn.clicked.connect(self._on_job_details)
        action_layout.addWidget(details_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        self.setLayout(layout)

        # 加载 Job 列表
        self._load_jobs()

    def _load_jobs(self):
        """加载 Job 列表"""
        self.job_list.clear()

        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import JobRun

                jobs = (
                    db_session.query(JobRun)
                    .order_by(JobRun.created_at.desc())
                    .limit(100)
                    .all()
                )

                for job in jobs:
                    # 状态图标
                    status_icon = {
                        "pending": "⏳",
                        "running": "▶️",
                        "success": "✅",
                        "failed": "❌",
                        "cancelled": "🚫",
                    }.get(job.status, "❓")

                    # 格式化时间
                    created_time = (
                        job.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if job.created_at
                        else "未知"
                    )

                    item_text = f"{status_icon} {job.name}\n"
                    item_text += f"  类型: {job.type} | 时间: {created_time}"

                    if job.summary:
                        summary = job.summary[:50] + "..." if len(job.summary) > 50 else job.summary
                        item_text += f"\n  {summary}"

                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, job.id)
                    self.job_list.addItem(item)

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载运行记录失败: {str(e)}")

    def _on_job_selected(self, item: QListWidgetItem):
        """Job 选中"""
        job_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_job_id = job_id
        self.job_selected.emit(job_id)

    def _on_job_details(self, item: QListWidgetItem = None):
        """查看 Job 详情"""
        job_id = self.current_job_id
        if not job_id:
            QMessageBox.warning(self, "错误", "请先选择一个运行记录")
            return

        dialog = JobDetailsDialog(self.orchestrator, job_id, parent=self)
        dialog.exec()


class JobDetailsDialog(QDialog):
    """Job 详情对话框"""

    def __init__(self, orchestrator, job_id, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.job_id = job_id
        self.setWindowTitle("运行记录详情")
        self.resize(800, 600)
        self._init_ui()
        self._load_job_details()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # Job 基本信息
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # 步骤列表
        steps_label = QLabel("执行步骤:")
        steps_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(steps_label)

        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(5)
        self.steps_table.setHorizontalHeaderLabels(["索引", "类型", "名称", "状态", "耗时(ms)"])
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.steps_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.steps_table)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def _load_job_details(self):
        """加载 Job 详情"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import JobRun, JobStep

                job = db_session.query(JobRun).filter_by(id=self.job_id).first()
                if not job:
                    QMessageBox.warning(self, "错误", "未找到运行记录")
                    return

                # 显示基本信息
                info_text = f"<b>名称:</b> {job.name}<br>"
                info_text += f"<b>类型:</b> {job.type}<br>"
                info_text += f"<b>状态:</b> {job.status}<br>"
                if job.goal:
                    info_text += f"<b>目标:</b> {job.goal}<br>"
                if job.created_at:
                    info_text += f"<b>创建时间:</b> {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}<br>"
                if job.started_at:
                    info_text += f"<b>开始时间:</b> {job.started_at.strftime('%Y-%m-%d %H:%M:%S')}<br>"
                if job.ended_at:
                    info_text += f"<b>结束时间:</b> {job.ended_at.strftime('%Y-%m-%d %H:%M:%S')}<br>"
                if job.summary:
                    info_text += f"<b>总结:</b> {job.summary}<br>"
                if job.error:
                    info_text += f"<b style='color:red;'>错误:</b> {job.error}<br>"

                self.info_label.setText(info_text)

                # 加载步骤列表
                steps = (
                    db_session.query(JobStep)
                    .filter_by(job_id=self.job_id)
                    .order_by(JobStep.step_index)
                    .all()
                )

                self.steps_table.setRowCount(len(steps))
                for row, step in enumerate(steps):
                    self.steps_table.setItem(row, 0, QTableWidgetItem(str(step.step_index)))
                    self.steps_table.setItem(row, 1, QTableWidgetItem(step.step_type))
                    self.steps_table.setItem(row, 2, QTableWidgetItem(step.step_name))
                    self.steps_table.setItem(row, 3, QTableWidgetItem(step.status))
                    self.steps_table.setItem(
                        row, 4, QTableWidgetItem(str(step.duration_ms) if step.duration_ms else "-")
                    )

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载详情失败: {str(e)}")
