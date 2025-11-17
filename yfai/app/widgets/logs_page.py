"""日志查看页面"""

import csv
import json
from datetime import datetime
from pathlib import Path

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
    QSpinBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class LogsPage(QWidget):
    """日志查看页面"""

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.current_page = 1
        self.page_size = 50
        self.total_logs = 0
        self.current_logs = []
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

        export_btn = QPushButton("📁 导出")
        export_btn.clicked.connect(self._export_logs)
        toolbar.addWidget(export_btn)

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

        # 分页控件
        pagination = QHBoxLayout()
        pagination.addStretch()

        prev_btn = QPushButton("⬅️ 上一页")
        prev_btn.clicked.connect(self._prev_page)
        pagination.addWidget(prev_btn)

        self.page_label = QLabel("第 1 页 / 共 1 页")
        pagination.addWidget(self.page_label)

        next_btn = QPushButton("下一页 ➡️")
        next_btn.clicked.connect(self._next_page)
        pagination.addWidget(next_btn)

        pagination.addWidget(QLabel("每页显示:"))
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setMinimum(10)
        self.page_size_spin.setMaximum(200)
        self.page_size_spin.setSingleStep(10)
        self.page_size_spin.setValue(self.page_size)
        self.page_size_spin.valueChanged.connect(self._on_page_size_changed)
        pagination.addWidget(self.page_size_spin)

        pagination.addStretch()

        layout.addLayout(pagination)
        self.setLayout(layout)

    def _load_logs(self):
        """加载日志列表"""
        log_type = self.log_type_combo.currentText()
        level_filter = self.log_level_combo.currentText()
        all_logs = self._collect_logs(log_type)
        if level_filter != "全部":
            all_logs = [item for item in all_logs if item["level"] == level_filter]

        self.current_logs = all_logs
        self.total_logs = len(all_logs)

        # 计算总页数
        total_pages = max(1, (self.total_logs + self.page_size - 1) // self.page_size)
        if self.current_page > total_pages:
            self.current_page = max(1, total_pages)

        # 更新分页标签
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {total_pages} 页 (总计 {self.total_logs} 条)")

        # 获取当前页的日志
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_logs)
        logs = all_logs[start_idx:end_idx]

        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            timestamp = log["timestamp"]
            ts_text = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "-"
            self.table.setItem(row, 0, QTableWidgetItem(ts_text))
            self.table.setItem(row, 1, QTableWidgetItem(log["type"]))

            level_item = QTableWidgetItem(log["level"])
            level_colors = {
                "INFO": "#0984e3",
                "WARNING": "#fdcb6e",
                "ERROR": "#d63031",
                "CRITICAL": "#a41623",
            }
            level_item.setForeground(QColor(level_colors.get(log["level"], "#000")))
            self.table.setItem(row, 2, level_item)

            self.table.setItem(row, 3, QTableWidgetItem(log["message"]))
            details_widget = self._create_details_button(log["details"])
            self.table.setCellWidget(row, 4, details_widget)

        if not logs:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("-"))
            self.table.setItem(0, 1, QTableWidgetItem("提示"))
            self.table.setItem(0, 2, QTableWidgetItem("INFO"))
            self.table.setItem(0, 3, QTableWidgetItem("暂无符合条件的日志"))
            self.table.setCellWidget(0, 4, self._create_details_button(""))

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
        self._load_logs()

    def _clear_logs(self):
        """清空日志"""
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有日志吗？\n\n这将删除:\n- 工具调用记录\n- 审批记录\n- 智能体运行记录\n- 任务步骤记录\n\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import ToolCall, JobRun, JobStep

                    # 删除任务步骤记录
                    step_count = db_session.query(JobStep).delete()

                    # 删除任务运行记录
                    job_count = db_session.query(JobRun).delete()

                    # 删除工具调用记录
                    tool_count = db_session.query(ToolCall).delete()

                    db_session.commit()

                QMessageBox.information(
                    self,
                    "成功",
                    f"已清空所有日志记录:\n- 工具调用: {tool_count} 条\n- 任务运行: {job_count} 条\n- 任务步骤: {step_count} 条"
                )
                self._load_logs()
            except Exception as e:
                QMessageBox.critical(self, "失败", f"清空日志失败: {e}")

    def _prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self._load_logs()

    def _next_page(self):
        """下一页"""
        total_pages = max(1, (self.total_logs + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self._load_logs()

    def _on_page_size_changed(self, value: int):
        """每页显示数量改变"""
        self.page_size = value
        self.current_page = 1
        self._load_logs()

    def _export_logs(self):
        """导出日志"""
        if not self.current_logs:
            QMessageBox.information(self, "提示", "没有可导出的日志")
            return

        # 让用户选择导出格式
        reply = QMessageBox.question(
            self,
            "选择导出格式",
            "请选择导出格式:\n\nYes = CSV格式\nNo = JSON格式",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return

        export_format = "csv" if reply == QMessageBox.StandardButton.Yes else "json"

        # 选择保存路径
        default_filename = f"yfai_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            default_filename,
            f"{'CSV文件 (*.csv)' if export_format == 'csv' else 'JSON文件 (*.json)'}"
        )

        if not file_path:
            return

        try:
            if export_format == "csv":
                self._export_to_csv(file_path)
            else:
                self._export_to_json(file_path)

            QMessageBox.information(self, "成功", f"日志已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"导出日志失败: {e}")

    def _export_to_csv(self, file_path: str):
        """导出为CSV格式"""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['时间', '类型', '级别', '消息', '详情']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for log in self.current_logs:
                timestamp = log["timestamp"]
                ts_text = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "-"
                writer.writerow({
                    '时间': ts_text,
                    '类型': log["type"],
                    '级别': log["level"],
                    '消息': log["message"],
                    '详情': log["details"]
                })

    def _export_to_json(self, file_path: str):
        """导出为JSON格式"""
        export_data = []
        for log in self.current_logs:
            timestamp = log["timestamp"]
            ts_text = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else None
            export_data.append({
                'timestamp': ts_text,
                'type': log["type"],
                'level': log["level"],
                'message': log["message"],
                'details': log["details"]
            })

        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, ensure_ascii=False, indent=2)

    def _collect_logs(self, log_type: str):
        """从数据库收集日志"""
        rows = []
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import ToolCall, JobRun

                if log_type in ("全部", "工具调用", "审批记录"):
                    tool_calls = (
                        db_session.query(ToolCall)
                        .order_by(ToolCall.created_at.desc())
                        .limit(200)
                        .all()
                    )
                    for call in tool_calls:
                        entry_type = "工具调用"
                        if log_type == "审批记录" and not call.approved_by:
                            continue
                        if log_type == "审批记录":
                            entry_type = "审批记录"

                        level = "INFO"
                        if call.status in ("failed", "rejected"):
                            level = "ERROR"
                        elif call.status in ("pending", "timeout"):
                            level = "WARNING"
                        elif call.risk_level in ("high", "critical"):
                            level = "WARNING"

                        params = call.params or ""
                        message = f"{call.tool_name} ({call.status})"
                        details = (
                            f"风险: {call.risk_level} | 参数: {params}\n"
                            f"输出: {call.stdout or ''}\n错误: {call.error or ''}"
                        )
                        rows.append(
                            {
                                "timestamp": call.created_at,
                                "type": entry_type,
                                "level": level,
                                "message": message,
                                "details": details,
                            }
                        )

                if log_type in ("全部", "智能体运行", "系统事件"):
                    jobs = (
                        db_session.query(JobRun)
                        .order_by(JobRun.created_at.desc())
                        .limit(100)
                        .all()
                    )
                    for job in jobs:
                        entry_type = "智能体运行"
                        level = "INFO" if job.status == "success" else "ERROR"
                        message = f"{job.name} ({job.status})"
                        details = job.summary or job.error or job.goal or ""
                        rows.append(
                            {
                                "timestamp": job.created_at,
                                "type": entry_type,
                                "level": level,
                                "message": message,
                                "details": details,
                            }
                        )

                if log_type == "系统事件":
                    health = self.orchestrator.provider_manager.get_health_status()
                    for provider, healthy in health.items():
                        rows.append(
                            {
                                "timestamp": None,
                                "type": "系统事件",
                                "level": "INFO" if healthy else "ERROR",
                                "message": f"Provider {provider} 状态: {'正常' if healthy else '异常'}",
                                "details": "来自最近一次健康检查",
                            }
                        )

        except Exception as e:
            rows.append(
                {
                    "timestamp": None,
                    "type": "系统事件",
                    "level": "ERROR",
                    "message": "读取日志失败",
                    "details": str(e),
                }
            )

        return rows
