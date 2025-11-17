"""审批管理页面"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QComboBox,
    QLineEdit,
    QDialog,
    QTextEdit,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from yfai.store.db import AuditLog


class ApprovalDetailDialog(QDialog):
    """审批详情对话框"""

    def __init__(self, log_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.log_data = log_data
        self.setWindowTitle("审批详情")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout()

        info_layout.addRow("审批ID:", QLabel(str(self.log_data.get("id", ""))))
        info_layout.addRow("操作类型:", QLabel(self.log_data.get("action_type", "")))
        info_layout.addRow("工具名称:", QLabel(self.log_data.get("tool_name", "") or "N/A"))

        # 风险等级 - 带颜色
        risk_level = self.log_data.get("risk_level", "")
        risk_label = QLabel(risk_level.upper() if risk_level else "N/A")
        risk_colors = {
            "low": "#00b894",
            "medium": "#fdcb6e",
            "high": "#e17055",
            "critical": "#d63031",
        }
        if risk_level:
            color = risk_colors.get(risk_level.lower(), "#666")
            risk_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        info_layout.addRow("风险等级:", risk_label)

        # 审批状态 - 带颜色
        approval_status = self.log_data.get("approval_status", "")
        status_label = QLabel(approval_status or "N/A")
        status_colors = {
            "approved": "#00b894",
            "rejected": "#d63031",
            "timeout": "#fdcb6e",
        }
        if approval_status:
            color = status_colors.get(approval_status.lower(), "#666")
            status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        info_layout.addRow("审批状态:", status_label)

        info_layout.addRow("用户ID:", QLabel(self.log_data.get("user_id", "") or "N/A"))
        info_layout.addRow("IP地址:", QLabel(self.log_data.get("ip_address", "") or "N/A"))

        timestamp = self.log_data.get("timestamp")
        timestamp_str = timestamp if timestamp else "N/A"
        info_layout.addRow("时间戳:", QLabel(timestamp_str))

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 请求数据
        request_group = QGroupBox("请求数据")
        request_layout = QVBoxLayout()

        self.request_text = QTextEdit()
        self.request_text.setReadOnly(True)
        self.request_text.setMaximumHeight(150)
        request_data = self.log_data.get("request_data")
        if request_data:
            import json
            self.request_text.setPlainText(json.dumps(request_data, indent=2, ensure_ascii=False))
        else:
            self.request_text.setPlainText("(无请求数据)")
        request_layout.addWidget(self.request_text)

        request_group.setLayout(request_layout)
        layout.addWidget(request_group)

        # 结果数据
        result_group = QGroupBox("结果数据")
        result_layout = QVBoxLayout()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        result_data = self.log_data.get("result_data")
        if result_data:
            import json
            self.result_text.setPlainText(json.dumps(result_data, indent=2, ensure_ascii=False))
        else:
            self.result_text.setPlainText("(无结果数据)")
        result_layout.addWidget(self.result_text)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ApprovalsPage(QWidget):
    """审批管理页面"""

    approval_selected = pyqtSignal(dict)

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("🔐 审批管理")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("查看和管理所有审批记录")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        # 过滤器行
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("时间范围:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["全部", "最近24小时", "最近7天", "最近30天"])
        self.time_range_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.time_range_combo)

        filter_layout.addWidget(QLabel("风险等级:"))
        self.risk_filter_combo = QComboBox()
        self.risk_filter_combo.addItems(["全部", "Low", "Medium", "High", "Critical"])
        self.risk_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.risk_filter_combo)

        filter_layout.addWidget(QLabel("状态:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["全部", "Approved", "Rejected", "Timeout"])
        self.status_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.status_filter_combo)

        filter_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索工具名称...")
        self.search_input.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.search_input)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._load_data)
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #666; padding: 5px 0;")
        layout.addWidget(self.stats_label)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "时间", "操作类型", "工具名称", "风险等级", "状态", "用户", "IP", "会话ID"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

        layout.addWidget(self.table)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.view_detail_btn = QPushButton("查看详情")
        self.view_detail_btn.clicked.connect(self._view_detail)
        self.view_detail_btn.setEnabled(False)
        button_layout.addWidget(self.view_detail_btn)

        self.delete_btn = QPushButton("删除记录")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)

        self.clear_old_btn = QPushButton("清理旧记录")
        self.clear_old_btn.clicked.connect(self._clear_old_records)
        button_layout.addWidget(self.clear_old_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 选择改变时启用按钮
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_data(self):
        """从数据库加载审批记录"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                # 构建查询
                query = db_session.query(AuditLog).order_by(AuditLog.timestamp.desc())

                # 应用过滤器
                query = self._apply_filters(query)

                logs = query.all()
                self._populate_table(logs)

                # 更新统计信息
                total = db_session.query(AuditLog).count()
                filtered = len(logs)
                approved = sum(1 for log in logs if log.approval_status == "approved")
                rejected = sum(1 for log in logs if log.approval_status == "rejected")

                self.stats_label.setText(
                    f"总计: {total} | 已过滤: {filtered} | 已批准: {approved} | 已拒绝: {rejected}"
                )

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载审批记录失败: {e}")

    def _apply_filters(self, query):
        """应用过滤条件"""
        # 时间范围过滤
        time_range = self.time_range_combo.currentText()
        if time_range != "全部":
            now = datetime.utcnow()
            if time_range == "最近24小时":
                cutoff = now - timedelta(days=1)
            elif time_range == "最近7天":
                cutoff = now - timedelta(days=7)
            elif time_range == "最近30天":
                cutoff = now - timedelta(days=30)
            else:
                cutoff = None

            if cutoff:
                query = query.filter(AuditLog.timestamp >= cutoff)

        # 风险等级过滤
        risk_filter = self.risk_filter_combo.currentText()
        if risk_filter != "全部":
            query = query.filter(AuditLog.risk_level == risk_filter.lower())

        # 状态过滤
        status_filter = self.status_filter_combo.currentText()
        if status_filter != "全部":
            query = query.filter(AuditLog.approval_status == status_filter.lower())

        # 搜索过滤
        search_text = self.search_input.text().strip()
        if search_text:
            query = query.filter(AuditLog.tool_name.like(f"%{search_text}%"))

        return query

    def _populate_table(self, logs: List[AuditLog]):
        """填充表格数据"""
        self.table.setRowCount(0)

        for log in logs:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 时间
            timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else ""
            self.table.setItem(row, 0, QTableWidgetItem(timestamp))

            # 操作类型
            self.table.setItem(row, 1, QTableWidgetItem(log.action_type or ""))

            # 工具名称
            self.table.setItem(row, 2, QTableWidgetItem(log.tool_name or ""))

            # 风险等级 - 带颜色
            risk_item = QTableWidgetItem(log.risk_level.upper() if log.risk_level else "")
            risk_colors = {
                "low": QColor("#00b894"),
                "medium": QColor("#fdcb6e"),
                "high": QColor("#e17055"),
                "critical": QColor("#d63031"),
            }
            if log.risk_level:
                risk_item.setForeground(risk_colors.get(log.risk_level.lower(), QColor("#666")))
            self.table.setItem(row, 3, risk_item)

            # 状态 - 带颜色
            status_item = QTableWidgetItem(log.approval_status.upper() if log.approval_status else "")
            status_colors = {
                "approved": QColor("#00b894"),
                "rejected": QColor("#d63031"),
                "timeout": QColor("#fdcb6e"),
            }
            if log.approval_status:
                status_item.setForeground(status_colors.get(log.approval_status.lower(), QColor("#666")))
            self.table.setItem(row, 4, status_item)

            # 用户
            self.table.setItem(row, 5, QTableWidgetItem(log.user_id or ""))

            # IP
            self.table.setItem(row, 6, QTableWidgetItem(log.ip_address or ""))

            # 会话ID
            session_id = log.session_id[:8] if log.session_id else ""
            self.table.setItem(row, 7, QTableWidgetItem(session_id))

            # 存储完整数据
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, log.to_dict())

    def _on_filter_changed(self):
        """过滤条件改变时重新加载数据"""
        self._load_data()

    def _on_selection_changed(self):
        """选择改变时启用/禁用按钮"""
        has_selection = len(self.table.selectedItems()) > 0
        self.view_detail_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def _on_row_double_clicked(self, row, column):
        """双击行时查看详情"""
        self._view_detail()

    def _view_detail(self):
        """查看选中记录的详情"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        log_data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        dialog = ApprovalDetailDialog(log_data, self)
        dialog.exec()

    def _delete_selected(self):
        """删除选中的记录"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        log_data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        log_id = log_data.get("id")

        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除这条审批记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    log = db_session.query(AuditLog).filter_by(id=log_id).first()
                    if log:
                        db_session.delete(log)
                        db_session.commit()
                        self._load_data()
                        QMessageBox.information(self, "成功", "审批记录已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除记录失败: {e}")

    def _clear_old_records(self):
        """清理旧记录（超过30天）"""
        reply = QMessageBox.question(
            self,
            "确认清理",
            "确定要清理超过30天的审批记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                cutoff = datetime.utcnow() - timedelta(days=30)
                with self.orchestrator.db_manager.get_session() as db_session:
                    deleted_count = db_session.query(AuditLog).filter(
                        AuditLog.timestamp < cutoff
                    ).delete()
                    db_session.commit()

                self._load_data()
                QMessageBox.information(self, "成功", f"已清理 {deleted_count} 条旧记录")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清理记录失败: {e}")

    def refresh(self):
        """刷新数据"""
        self._load_data()
