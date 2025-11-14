"""自动化任务管理页面"""

import json
import uuid
from datetime import datetime
from typing import Optional

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
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class AutomationDialog(QDialog):
    """自动化任务编辑对话框"""

    def __init__(self, orchestrator, task: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.task = task
        self.is_edit = task is not None

        self.setWindowTitle("编辑任务" if self.is_edit else "创建任务")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._init_ui()
        if self.is_edit:
            self._load_task_data()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 表单
        form_layout = QFormLayout()

        # 任务名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("任务名称")
        form_layout.addRow("名称:", self.name_edit)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("任务描述")
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow("描述:", self.description_edit)

        # 触发类型
        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.addItems([
            "interval (定时间隔)",
            "once (一次性)",
            "cron (Cron表达式)",
            "file (文件监听)",
            "process (进程监听)",
            "webhook (HTTP触发)",
        ])
        self.trigger_type_combo.currentIndexChanged.connect(self._on_trigger_type_changed)
        form_layout.addRow("触发类型:", self.trigger_type_combo)

        # 触发配置区域
        self.trigger_config_widget = QWidget()
        self.trigger_config_layout = QVBoxLayout(self.trigger_config_widget)
        self.trigger_config_layout.setContentsMargins(0, 0, 0, 0)

        # Interval 配置
        self.interval_widget = QWidget()
        interval_layout = QFormLayout(self.interval_widget)
        self.interval_seconds = QSpinBox()
        self.interval_seconds.setRange(1, 86400)  # 1秒 - 24小时
        self.interval_seconds.setValue(60)
        self.interval_seconds.setSuffix(" 秒")
        interval_layout.addRow("间隔时间:", self.interval_seconds)
        self.trigger_config_layout.addWidget(self.interval_widget)

        # Cron 配置
        self.cron_widget = QWidget()
        cron_layout = QFormLayout(self.cron_widget)
        self.cron_expr = QLineEdit()
        self.cron_expr.setPlaceholderText("例如: 0 */6 * * * (每6小时)")
        cron_layout.addRow("Cron表达式:", self.cron_expr)
        cron_hint = QLabel("格式: 分 时 日 月 周")
        cron_hint.setStyleSheet("color: #666; font-size: 10pt;")
        cron_layout.addRow("", cron_hint)
        self.trigger_config_layout.addWidget(self.cron_widget)
        self.cron_widget.setVisible(False)

        # File 配置
        self.file_widget = QWidget()
        file_layout = QFormLayout(self.file_widget)
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("监听的文件路径或目录")
        file_layout.addRow("文件路径:", self.file_path)
        self.file_pattern = QLineEdit()
        self.file_pattern.setPlaceholderText("*.txt")
        file_layout.addRow("文件模式:", self.file_pattern)
        self.trigger_config_layout.addWidget(self.file_widget)
        self.file_widget.setVisible(False)

        # Process 配置
        self.process_widget = QWidget()
        process_layout = QFormLayout(self.process_widget)
        self.process_name = QLineEdit()
        self.process_name.setPlaceholderText("进程名称")
        process_layout.addRow("进程名称:", self.process_name)
        self.process_event = QComboBox()
        self.process_event.addItems(["started (启动)", "stopped (停止)"])
        process_layout.addRow("监听事件:", self.process_event)
        self.trigger_config_layout.addWidget(self.process_widget)
        self.process_widget.setVisible(False)

        # Webhook 配置
        self.webhook_widget = QWidget()
        webhook_layout = QFormLayout(self.webhook_widget)
        self.webhook_path = QLineEdit()
        self.webhook_path.setPlaceholderText("/webhook/my-task")
        webhook_layout.addRow("Webhook路径:", self.webhook_path)
        webhook_hint = QLabel("任务将在收到HTTP POST请求时触发")
        webhook_hint.setStyleSheet("color: #666; font-size: 10pt;")
        webhook_layout.addRow("", webhook_hint)
        self.trigger_config_layout.addWidget(self.webhook_widget)
        self.webhook_widget.setVisible(False)

        form_layout.addRow("触发配置:", self.trigger_config_widget)

        # 智能体选择
        self.agent_combo = QComboBox()
        self._load_agents()
        form_layout.addRow("执行智能体:", self.agent_combo)

        # 执行目标
        self.goal_edit = QTextEdit()
        self.goal_edit.setPlaceholderText("智能体要完成的目标描述")
        self.goal_edit.setMaximumHeight(100)
        form_layout.addRow("执行目标:", self.goal_edit)

        # 是否启用
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        form_layout.addRow("启用:", self.enabled_check)

        layout.addLayout(form_layout)

        # 按钮
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def _on_trigger_type_changed(self, index: int):
        """触发类型改变"""
        # 隐藏所有配置
        self.interval_widget.setVisible(False)
        self.cron_widget.setVisible(False)
        self.file_widget.setVisible(False)
        self.process_widget.setVisible(False)
        self.webhook_widget.setVisible(False)

        # 显示对应的配置
        if index == 0:  # interval
            self.interval_widget.setVisible(True)
        elif index == 1:  # once
            pass  # 一次性任务不需要额外配置
        elif index == 2:  # cron
            self.cron_widget.setVisible(True)
        elif index == 3:  # file
            self.file_widget.setVisible(True)
        elif index == 4:  # process
            self.process_widget.setVisible(True)
        elif index == 5:  # webhook
            self.webhook_widget.setVisible(True)

    def _load_agents(self):
        """加载智能体列表"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Agent

                agents = db_session.query(Agent).filter_by(is_enabled=True).all()
                for agent in agents:
                    self.agent_combo.addItem(agent.name, agent.id)
        except Exception as e:
            print(f"加载智能体失败: {e}")

    def _load_task_data(self):
        """加载任务数据"""
        if not self.task:
            return

        self.name_edit.setText(self.task.get("name", ""))
        self.description_edit.setPlainText(self.task.get("description", ""))

        # 触发类型
        trigger_type = self.task.get("trigger_type", "interval")
        trigger_map = {
            "interval": 0,
            "once": 1,
            "cron": 2,
            "file": 3,
            "process": 4,
            "webhook": 5,
        }
        self.trigger_type_combo.setCurrentIndex(trigger_map.get(trigger_type, 0))

        # 触发配置
        if trigger_type == "interval":
            self.interval_seconds.setValue(self.task.get("interval_seconds", 60))
        elif trigger_type == "cron":
            self.cron_expr.setText(self.task.get("cron_expr", ""))
        elif trigger_type in ["file", "process", "webhook"]:
            event_config = self.task.get("event_config", {})
            if isinstance(event_config, str):
                event_config = json.loads(event_config)

            if trigger_type == "file":
                self.file_path.setText(event_config.get("path", ""))
                self.file_pattern.setText(event_config.get("pattern", ""))
            elif trigger_type == "process":
                self.process_name.setText(event_config.get("name", ""))
                event = event_config.get("event", "started")
                self.process_event.setCurrentText(f"{event} ({'启动' if event == 'started' else '停止'})")
            elif trigger_type == "webhook":
                self.webhook_path.setText(event_config.get("path", ""))

        # 智能体
        agent_id = self.task.get("agent_id")
        if agent_id:
            for i in range(self.agent_combo.count()):
                if self.agent_combo.itemData(i) == agent_id:
                    self.agent_combo.setCurrentIndex(i)
                    break

        # 目标
        self.goal_edit.setPlainText(self.task.get("goal", ""))

        # 是否启用
        self.enabled_check.setChecked(self.task.get("enabled", True))

    def get_task_data(self) -> dict:
        """获取任务数据"""
        trigger_index = self.trigger_type_combo.currentIndex()
        trigger_types = ["interval", "once", "cron", "file", "process", "webhook"]
        trigger_type = trigger_types[trigger_index]

        data = {
            "name": self.name_edit.text(),
            "description": self.description_edit.toPlainText(),
            "trigger_type": trigger_type,
            "agent_id": self.agent_combo.currentData(),
            "goal": self.goal_edit.toPlainText(),
            "enabled": self.enabled_check.isChecked(),
        }

        # 触发配置
        if trigger_type == "interval":
            data["interval_seconds"] = self.interval_seconds.value()
        elif trigger_type == "cron":
            data["cron_expr"] = self.cron_expr.text()
        elif trigger_type == "file":
            data["event_config"] = json.dumps({
                "path": self.file_path.text(),
                "pattern": self.file_pattern.text(),
            })
        elif trigger_type == "process":
            event = self.process_event.currentText().split()[0]
            data["event_config"] = json.dumps({
                "name": self.process_name.text(),
                "event": event,
            })
        elif trigger_type == "webhook":
            data["event_config"] = json.dumps({
                "path": self.webhook_path.text(),
            })

        return data


class AutomationPage(QWidget):
    """自动化任务管理页面"""

    task_triggered = pyqtSignal(str)  # 任务ID

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_tasks()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 顶部工具栏
        toolbar = QHBoxLayout()

        create_btn = QPushButton("➕ 创建任务")
        create_btn.clicked.connect(self._create_task)
        toolbar.addWidget(create_btn)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_tasks)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 任务列表
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "名称", "触发类型", "智能体", "状态", "最后运行",
            "运行次数", "操作", "ID"
        ])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnHidden(7, True)  # 隐藏ID列

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _load_tasks(self):
        """加载任务列表"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import AutomationTask

                tasks = db_session.query(AutomationTask).all()
                self.table.setRowCount(len(tasks))

                for row, task in enumerate(tasks):
                    # 名称
                    self.table.setItem(row, 0, QTableWidgetItem(task.name))

                    # 触发类型
                    self.table.setItem(row, 1, QTableWidgetItem(task.trigger_type))

                    # 智能体
                    agent_name = task.agent.name if task.agent else "-"
                    self.table.setItem(row, 2, QTableWidgetItem(agent_name))

                    # 状态
                    status_item = QTableWidgetItem("✓ 启用" if task.enabled else "✗ 禁用")
                    if task.enabled:
                        status_item.setForeground(QColor("#00b894"))
                    else:
                        status_item.setForeground(QColor("#b2bec3"))
                    self.table.setItem(row, 3, status_item)

                    # 最后运行
                    last_run = task.last_run_at.strftime("%Y-%m-%d %H:%M") if task.last_run_at else "-"
                    self.table.setItem(row, 4, QTableWidgetItem(last_run))

                    # 运行次数
                    self.table.setItem(row, 5, QTableWidgetItem(str(task.run_count)))

                    # 操作按钮
                    actions_widget = self._create_action_buttons(task.id, task.enabled)
                    self.table.setCellWidget(row, 6, actions_widget)

                    # ID (隐藏)
                    self.table.setItem(row, 7, QTableWidgetItem(task.id))

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载任务列表失败: {e}")

    def _create_action_buttons(self, task_id: str, enabled: bool) -> QWidget:
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 运行按钮
        run_btn = QPushButton("▶")
        run_btn.setMaximumWidth(30)
        run_btn.setToolTip("手动运行")
        run_btn.clicked.connect(lambda: self._run_task(task_id))
        layout.addWidget(run_btn)

        # 编辑按钮
        edit_btn = QPushButton("✎")
        edit_btn.setMaximumWidth(30)
        edit_btn.setToolTip("编辑")
        edit_btn.clicked.connect(lambda: self._edit_task(task_id))
        layout.addWidget(edit_btn)

        # 启用/禁用按钮
        toggle_btn = QPushButton("⏸" if enabled else "▶")
        toggle_btn.setMaximumWidth(30)
        toggle_btn.setToolTip("禁用" if enabled else "启用")
        toggle_btn.clicked.connect(lambda: self._toggle_task(task_id))
        layout.addWidget(toggle_btn)

        # 删除按钮
        delete_btn = QPushButton("🗑")
        delete_btn.setMaximumWidth(30)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda: self._delete_task(task_id))
        layout.addWidget(delete_btn)

        return widget

    def _create_task(self):
        """创建任务"""
        dialog = AutomationDialog(self.orchestrator, parent=self)
        if dialog.exec():
            try:
                data = dialog.get_task_data()
                data["id"] = str(uuid.uuid4())

                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import AutomationTask

                    task = AutomationTask(**data)
                    db_session.add(task)
                    db_session.commit()

                QMessageBox.information(self, "成功", "任务创建成功")
                self._load_tasks()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建任务失败: {e}")

    def _edit_task(self, task_id: str):
        """编辑任务"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import AutomationTask

                task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                if not task:
                    QMessageBox.warning(self, "警告", "任务不存在")
                    return

                task_dict = task.to_dict()

            dialog = AutomationDialog(self.orchestrator, task_dict, parent=self)
            if dialog.exec():
                data = dialog.get_task_data()

                with self.orchestrator.db_manager.get_session() as db_session:
                    task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                    if task:
                        for key, value in data.items():
                            setattr(task, key, value)
                        task.updated_at = datetime.utcnow()
                        db_session.commit()

                QMessageBox.information(self, "成功", "任务更新成功")
                self._load_tasks()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑任务失败: {e}")

    def _run_task(self, task_id: str):
        """手动运行任务"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要手动运行此任务吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 触发任务运行
                # TODO: 调用 orchestrator 的方法来运行任务
                self.task_triggered.emit(task_id)
                QMessageBox.information(self, "成功", "任务已触发运行")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"运行任务失败: {e}")

    def _toggle_task(self, task_id: str):
        """切换任务启用状态"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import AutomationTask

                task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                if task:
                    task.enabled = not task.enabled
                    task.updated_at = datetime.utcnow()
                    db_session.commit()

                    status = "启用" if task.enabled else "禁用"
                    QMessageBox.information(self, "成功", f"任务已{status}")
                    self._load_tasks()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"切换任务状态失败: {e}")

    def _delete_task(self, task_id: str):
        """删除任务"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除此任务吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import AutomationTask

                    task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                    if task:
                        db_session.delete(task)
                        db_session.commit()

                QMessageBox.information(self, "成功", "任务已删除")
                self._load_tasks()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除任务失败: {e}")
