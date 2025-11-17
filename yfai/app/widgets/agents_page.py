"""智能体管理页面"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QLineEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


AVAILABLE_AGENT_TOOLS = [
    {
        "id": "shell.exec",
        "name": "Shell 执行",
        "description": "在本地执行命令",
        "risk": "高",
    },
    {
        "id": "fs.read",
        "name": "读取文件",
        "description": "查看文件内容",
        "risk": "低",
    },
    {
        "id": "fs.write",
        "name": "写入文件",
        "description": "创建/覆盖文件",
        "risk": "中",
    },
    {
        "id": "fs.list",
        "name": "列出目录",
        "description": "浏览目录结构",
        "risk": "低",
    },
    {
        "id": "process.list",
        "name": "进程列表",
        "description": "查看正在运行的进程",
        "risk": "低",
    },
    {
        "id": "process.info",
        "name": "进程详情",
        "description": "查询单个进程",
        "risk": "中",
    },
    {
        "id": "net.http",
        "name": "HTTP 请求",
        "description": "访问外部 HTTP 服务",
        "risk": "中",
    },
    {
        "id": "net.check_port",
        "name": "端口探测",
        "description": "检查本地端口状态",
        "risk": "低",
    },
    {
        "id": "net.local_ip",
        "name": "本地主机信息",
        "description": "获取本地 IP",
        "risk": "低",
    },
]

DEFAULT_ALLOWED_TOOLS = [
    "shell.exec",
    "fs.read",
    "fs.write",
    "fs.list",
    "process.list",
    "process.info",
    "net.http",
    "net.check_port",
    "net.local_ip",
]


class AgentsPage(QWidget):
    """智能体管理页面"""

    agent_selected = pyqtSignal(str)  # agent_id

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.current_agent_id = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("智能体管理")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 新建按钮
        new_btn = QPushButton("+ 新建智能体")
        new_btn.clicked.connect(self._on_create_agent)
        title_layout.addWidget(new_btn)

        edit_btn = QPushButton("✎ 编辑选中")
        edit_btn.clicked.connect(self._on_edit_agent)
        title_layout.addWidget(edit_btn)

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_agents)
        title_layout.addWidget(refresh_btn)

        layout.addLayout(title_layout)

        # 智能体列表
        self.agent_list = QListWidget()
        self.agent_list.itemClicked.connect(self._on_agent_selected)
        self.agent_list.itemDoubleClicked.connect(self._on_agent_double_clicked)
        layout.addWidget(self.agent_list)

        # 运行控制区
        run_layout = QHBoxLayout()
        run_label = QLabel("目标:")
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("输入智能体要完成的目标...")
        self.run_provider_combo = QComboBox()
        self.run_provider_combo.addItem("使用默认", "")
        self.run_provider_combo.addItem("百炼(DashScope)", "bailian")
        self.run_provider_combo.addItem("Ollama", "ollama")
        self.run_provider_combo.currentTextChanged.connect(self._on_run_provider_changed)
        self.run_model_combo = QComboBox()
        self.run_model_combo.setEditable(True)
        self.run_model_combo.lineEdit().setPlaceholderText("跟随智能体默认模型")
        run_btn = QPushButton("▶ 运行")
        run_btn.clicked.connect(self._on_run_agent)
        stop_btn = QPushButton("⏹ 终止")
        stop_btn.clicked.connect(self._request_stop)
        run_layout.addWidget(run_label)
        run_layout.addWidget(self.goal_input)
        run_layout.addWidget(QLabel("Provider:"))
        run_layout.addWidget(self.run_provider_combo)
        run_layout.addWidget(QLabel("模型:"))
        run_layout.addWidget(self.run_model_combo)
        run_layout.addWidget(run_btn)
        run_layout.addWidget(stop_btn)
        layout.addLayout(run_layout)
        self._populate_run_models(self.run_provider_combo.currentData())

        self.run_log_output = QTextEdit()
        self.run_log_output.setReadOnly(True)
        self.run_log_output.setPlaceholderText("实时步骤日志将在此显示…")
        self.run_log_output.setMinimumHeight(160)
        layout.addWidget(self.run_log_output)

        self.run_summary_output = QTextEdit()
        self.run_summary_output.setReadOnly(True)
        self.run_summary_output.setPlaceholderText("执行完成后将在此显示总结与计划…")
        self.run_summary_output.setMinimumHeight(140)
        layout.addWidget(self.run_summary_output)

        self.setLayout(layout)

        # 加载智能体列表
        self._load_agents()
        self._progress_task: Optional[asyncio.Task] = None
        self._progress_stop: Optional[asyncio.Event] = None

    def _load_agents(self):
        """加载智能体列表"""
        self.agent_list.clear()

        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Agent

                agents = db_session.query(Agent).order_by(Agent.created_at.desc()).all()

                for agent in agents:
                    item_text = f"{'✓' if agent.is_enabled else '✗'} {agent.name}"
                    if agent.description:
                        item_text += f"\n  {agent.description}"

                    workflow_info = ""
                    if agent.stop_condition:
                        try:
                            workflow_data = json.loads(agent.stop_condition)
                            steps = workflow_data.get("workflow_steps", [])
                            if steps:
                                workflow_info = f"🧠 预设 {len(steps)} 步"
                        except Exception:
                            workflow_info = ""

                    if workflow_info:
                        item_text += f"\n  {workflow_info}"

                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, agent.id)
                    self.agent_list.addItem(item)

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载智能体列表失败: {str(e)}")

    def _on_agent_selected(self, item: QListWidgetItem):
        """智能体选中"""
        agent_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_agent_id = agent_id
        self.agent_selected.emit(agent_id)

    def _on_agent_double_clicked(self, item: QListWidgetItem):
        """双击编辑"""
        self.current_agent_id = item.data(Qt.ItemDataRole.UserRole)
        self._on_edit_agent()

    def _on_create_agent(self):
        """创建新智能体"""
        dialog = AgentEditDialog(self.orchestrator, parent=self)
        if dialog.exec():
            self._load_agents()

    def _on_edit_agent(self):
        """编辑当前智能体"""
        if not self.current_agent_id:
            QMessageBox.information(self, "提示", "请先选择一个智能体")
            return

        dialog = AgentEditDialog(self.orchestrator, agent_id=self.current_agent_id, parent=self)
        if dialog.exec():
            self._load_agents()

    def _on_run_agent(self):
        """运行智能体"""
        if not self.current_agent_id:
            QMessageBox.warning(self, "错误", "请先选择一个智能体")
            return

        goal = self.goal_input.text().strip()
        if not goal:
            QMessageBox.warning(self, "错误", "请输入目标")
            return

        # 异步运行智能体
        asyncio.create_task(self._run_agent_async(self.current_agent_id, goal))
        QMessageBox.information(self, "成功", "智能体已开始执行")

    async def _run_agent_async(self, agent_id: str, goal: str):
        """异步运行智能体"""
        try:
            self._cancel_progress_watcher()
            self.run_log_output.clear()
            self.run_summary_output.clear()

            agent_info = self._get_agent(agent_id)
            context: Dict[str, Any] = {}
            provider_val = self.run_provider_combo.currentData()
            model_val = self.run_model_combo.currentText().strip()
            if provider_val:
                context["provider_override"] = provider_val
            if model_val:
                context["model_override"] = model_val

            provider_label = provider_val or agent_info.get("default_provider") or "auto"
            model_label = model_val or agent_info.get("default_model") or "默认"
            self._append_log(f"启动智能体: {agent_info.get('name')} (Provider: {provider_label}, 模型: {model_label})")
            self._append_log(f"目标: {goal}")

            start_marker = datetime.utcnow()
            self._progress_stop = asyncio.Event()
            self._progress_task = asyncio.create_task(
                self._poll_job_progress(agent_id, start_marker, self._progress_stop)
            )

            result = await self.orchestrator.run_agent(
                agent_id, goal, context=context or None
            )

            if self._progress_stop:
                self._progress_stop.set()
            if self._progress_task:
                try:
                    await self._progress_task
                except asyncio.CancelledError:
                    pass
            self._progress_stop = None
            self._progress_task = None

            summary = self._format_run_result(result)
            self.run_summary_output.setPlainText(summary)
            self._append_log(f"执行完成: {result.get('status')}")
        except Exception as e:
            if self._progress_stop:
                self._progress_stop.set()
            if self._progress_task:
                try:
                    await self._progress_task
                except asyncio.CancelledError:
                    pass
            self._progress_stop = None
            self._progress_task = None
            self.run_summary_output.setPlainText(f"运行失败: {e}")
            print(f"Agent run failed: {e}")

    def _on_run_provider_changed(self, _text: str) -> None:
        """运行时 Provider 切换"""
        provider = self.run_provider_combo.currentData()
        self._populate_run_models(provider)

    def _populate_run_models(self, provider: Optional[str]) -> None:
        """刷新运行时模型下拉"""
        current_text = self.run_model_combo.currentText().strip()
        self.run_model_combo.blockSignals(True)
        self.run_model_combo.clear()
        if provider:
            models = self.orchestrator.provider_manager.get_configured_models(provider)
            for item in models:
                if isinstance(item, dict):
                    code = item.get("code") or item.get("name")
                    display = item.get("name", code)
                    if item.get("name") and code:
                        display = f"{item['name']} ({code})"
                    self.run_model_combo.addItem(display, code)
                else:
                    self.run_model_combo.addItem(str(item), str(item))
            placeholder = "输入或选择模型 (可留空)"
        else:
            placeholder = "跟随智能体默认模型"
        self.run_model_combo.lineEdit().setPlaceholderText(placeholder)
        if current_text:
            self.run_model_combo.setEditText(current_text)
        self.run_model_combo.blockSignals(False)

    def _format_run_result(self, result: dict) -> str:
        """将运行结果格式化为多行文本"""
        lines: List[str] = []
        status = result.get("status")
        lines.append(f"状态: {status}")
        if result.get("job_id"):
            lines.append(f"Job ID: {result['job_id']}")
        if result.get("summary"):
            lines.append("\n总结:")
            lines.append(result["summary"])

        plan = result.get("plan") or {}
        steps = plan.get("steps") or []
        if steps:
            lines.append("\n计划步骤:")
            for step in steps:
                name = step.get("name") or f"步骤 {step.get('index', 0)}"
                desc = step.get("description") or ""
                lines.append(f"- {name} [{step.get('type')}] {desc}")

        results = result.get("results") or []
        if results:
            lines.append("\n执行结果:")
            for step_result in results:
                idx = step_result.get("step_index")
                status = step_result.get("status")
                err = step_result.get("error")
                res = step_result.get("result") or {}
                snippet = ""
                if isinstance(res, dict) and res.get("content"):
                    snippet = res["content"][:120]
                elif isinstance(res, dict):
                    snippet = str(res)[:120]
                lines.append(
                    f"- Step {idx}: {status}"
                    + (f" | {snippet}" if snippet else "")
                    + (f" | 错误: {err}" if err else "")
                )

        return "\n".join(lines)

    def _append_log(self, text: str) -> None:
        """追加实时日志"""
        self.run_log_output.append(text)

    def _get_agent(self, agent_id: str) -> Dict[str, Any]:
        """获取智能体信息"""
        with self.orchestrator.db_manager.get_session() as db_session:
            from yfai.store.db import Agent

            agent = db_session.query(Agent).filter_by(id=agent_id).first()
            if not agent:
                raise ValueError("未找到智能体")
            return agent.to_dict()

    def _cancel_progress_watcher(self) -> None:
        """取消正在运行的进度轮询"""
        if self._progress_stop:
            self._progress_stop.set()
        if self._progress_task:
            self._progress_task.cancel()
        self._progress_stop = None
        self._progress_task = None

    def _request_stop(self) -> None:
        """终止按钮（占位）"""
        self._append_log("终止功能尚未实现")

    async def _poll_job_progress(
        self,
        agent_id: str,
        start_marker: datetime,
        stop_event: asyncio.Event,
    ) -> None:
        """轮询数据库，实时显示 JobRun/JobStep"""
        from yfai.store.db import JobRun, JobStep

        job_id: Optional[str] = None
        last_logged_step = -1
        last_status = None
        tolerance = start_marker - timedelta(seconds=2)

        while not stop_event.is_set():
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    if not job_id:
                        job = (
                            db_session.query(JobRun)
                            .filter(JobRun.agent_id == agent_id)
                            .order_by(JobRun.created_at.desc())
                            .first()
                        )
                        if job and job.created_at >= tolerance:
                            job_id = job.id
                            self._append_log(f"Job {job_id} 状态: {job.status}")

                    if job_id:
                        job = db_session.query(JobRun).filter_by(id=job_id).first()
                        if job:
                            steps = (
                                db_session.query(JobStep)
                                .filter_by(job_id=job_id)
                                .order_by(JobStep.step_index)
                                .all()
                            )
                            for step in steps:
                                if (
                                    step.step_index is not None
                                    and step.step_index > last_logged_step
                                ):
                                    desc = step.step_name or step.step_type
                                    self._append_log(
                                        f"[Step {step.step_index}] {desc} -> {step.status}"
                                    )
                                    last_logged_step = step.step_index

                            if job.status != last_status:
                                self._append_log(f"Job {job_id} 状态: {job.status}")
                                last_status = job.status

                            if job.status in {"failed", "success", "cancelled"}:
                                self._append_log(f"Job {job_id} 完成: {job.status}")
                                stop_event.set()
                                break
            except Exception:
                pass

            await asyncio.sleep(1)


class AgentEditDialog(QDialog):
    """智能体编辑对话框"""

    def __init__(self, orchestrator, agent_id=None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.agent_id = agent_id
        self.original_tools: list[str] | None = None
        self.setWindowTitle("新建智能体" if not agent_id else "编辑智能体")
        self.resize(720, 640)
        self._init_ui()
        if self.agent_id:
            self._load_agent()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_basic_tab(), "基础配置")
        self.tabs.addTab(self._create_model_tab(), "模型与上下文")
        self.tabs.addTab(self._create_tools_tab(), "工具权限")
        self.tabs.addTab(self._create_workflow_tab(), "多步骤编排")
        layout.addWidget(self.tabs)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        layout.addWidget(buttons)
        self._on_provider_changed(self.provider_combo.currentText())

    def _create_basic_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.name_input = QLineEdit()
        form.addRow("名称:", self.name_input)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("简要说明智能体的职责与特长")
        self.desc_input.setMaximumHeight(70)
        form.addRow("描述:", self.desc_input)

        self.enabled_check = QCheckBox("启用智能体")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)

        self.max_steps_spin = QSpinBox()
        self.max_steps_spin.setRange(1, 50)
        self.max_steps_spin.setValue(10)
        self.max_steps_spin.setSuffix(" 步")
        form.addRow("最大执行步数:", self.max_steps_spin)

        return widget

    def _create_model_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["bailian", "ollama", "auto"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        form.addRow("Provider:", self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        form.addRow("默认模型:", self.model_combo)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("输入系统提示词，例如角色、能力和风格约束")
        self.prompt_input.setMinimumHeight(160)
        form.addRow("系统提示词:", self.prompt_input)

        return widget

    def _create_tools_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("勾选允许智能体调用的工具："))

        self.tools_table = QTableWidget()
        self.tools_table.setColumnCount(3)
        self.tools_table.setHorizontalHeaderLabels(["启用", "工具", "说明"])
        header = self.tools_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tools_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tools_table)

        self._populate_tools_table()
        return widget

    def _create_workflow_tab(self) -> QWidget:
        widget = QWidget()
        workflow_layout = QVBoxLayout(widget)

        workflow_desc = QLabel("为智能体预置多步骤编排。执行任务时将先按顺序完成这些步骤，再根据结果继续推理。")
        workflow_desc.setWordWrap(True)
        workflow_desc.setStyleSheet("color: #666;")
        workflow_layout.addWidget(workflow_desc)

        self.workflow_table = QTableWidget()
        self.workflow_table.setColumnCount(4)
        self.workflow_table.setHorizontalHeaderLabels(["步骤名称", "类型", "动作/工具", "说明"])
        header = self.workflow_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        workflow_layout.addWidget(self.workflow_table)

        workflow_buttons = QHBoxLayout()
        add_step_btn = QPushButton("添加步骤")
        add_step_btn.clicked.connect(self._add_workflow_row)
        workflow_buttons.addWidget(add_step_btn)

        remove_step_btn = QPushButton("删除选中")
        remove_step_btn.clicked.connect(self._remove_workflow_row)
        workflow_buttons.addWidget(remove_step_btn)
        workflow_buttons.addStretch()
        workflow_layout.addLayout(workflow_buttons)

        return widget

    def _load_agent(self) -> None:
        """加载已有智能体数据"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Agent

                agent = db_session.query(Agent).filter_by(id=self.agent_id).first()
                if not agent:
                    QMessageBox.warning(self, "提示", "未找到智能体")
                    return

                self.name_input.setText(agent.name)
                self.desc_input.setPlainText(agent.description or "")
                self.prompt_input.setPlainText(agent.system_prompt or "")
                self.provider_combo.setCurrentText(agent.default_provider or "bailian")
                self._set_model_value(agent.default_model or "")
                self.max_steps_spin.setValue(agent.max_steps or 10)
                self.enabled_check.setChecked(agent.is_enabled)
                try:
                    self.original_tools = json.loads(agent.allowed_tools) if agent.allowed_tools else None
                except Exception:
                    self.original_tools = None
                self._populate_tools_table(self.original_tools)

                if agent.stop_condition:
                    try:
                        workflow = json.loads(agent.stop_condition)
                        steps = workflow.get("workflow_steps", [])
                        for step in steps:
                            self._add_workflow_row(step)
                    except Exception:
                        pass
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"加载智能体失败: {exc}")

    def _on_accept(self):
        """确认创建/编辑"""
        import uuid

        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入智能体名称")
            return

        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "错误", "请输入系统提示词")
            return

        workflow_steps = self._collect_workflow_steps()
        workflow_data = {"workflow_steps": workflow_steps} if workflow_steps else None

        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Agent
                from datetime import datetime

                if self.agent_id:
                    # 编辑现有智能体
                    agent = db_session.query(Agent).filter_by(id=self.agent_id).first()
                else:
                    # 创建新智能体
                    agent = Agent(id=str(uuid.uuid4()))

                agent.name = name
                agent.description = self.desc_input.toPlainText().strip()
                agent.system_prompt = prompt
                agent.default_provider = self.provider_combo.currentText()
                agent.default_model = self._get_selected_model()
                agent.max_steps = self.max_steps_spin.value()
                agent.is_enabled = self.enabled_check.isChecked()
                tools = self._collect_selected_tools()
                agent.allowed_tools = json.dumps(tools)
                agent.stop_condition = (
                    json.dumps(workflow_data, ensure_ascii=False) if workflow_data else None
                )

                if not self.agent_id:
                    db_session.add(agent)

                db_session.commit()

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def _add_workflow_row(self, step: Optional[dict] = None) -> None:
        row = self.workflow_table.rowCount()
        self.workflow_table.insertRow(row)

        name_item = QTableWidgetItem(step.get("name", "") if step else "")
        self.workflow_table.setItem(row, 0, name_item)

        type_combo = QComboBox()
        type_combo.addItems(["analysis", "model", "tool"])
        if step and step.get("type"):
            idx = type_combo.findText(step["type"])
            if idx >= 0:
                type_combo.setCurrentIndex(idx)
        self.workflow_table.setCellWidget(row, 1, type_combo)

        action_value = ""
        if step:
            action_value = step.get("tool") or step.get("prompt") or step.get("action") or ""
        self.workflow_table.setItem(row, 2, QTableWidgetItem(action_value))

        desc_item = QTableWidgetItem(step.get("description", "") if step else "")
        self.workflow_table.setItem(row, 3, desc_item)

    def _remove_workflow_row(self) -> None:
        indexes = self.workflow_table.selectionModel().selectedRows()
        for index in sorted(indexes, key=lambda i: i.row(), reverse=True):
            self.workflow_table.removeRow(index.row())

    def _collect_workflow_steps(self) -> List[dict]:
        steps: List[dict] = []
        for row in range(self.workflow_table.rowCount()):
            name = self.workflow_table.item(row, 0)
            desc = self.workflow_table.item(row, 3)
            action = self.workflow_table.item(row, 2)
            type_combo = self.workflow_table.cellWidget(row, 1)

            step_type = type_combo.currentText() if type_combo else "analysis"
            step_data = {
                "index": row,
                "type": step_type,
                "name": (name.text().strip() if name and name.text() else f"步骤 {row + 1}"),
                "description": desc.text().strip() if desc else "",
            }

            action_text = action.text().strip() if action else ""
            if step_type == "tool" and action_text:
                step_data["tool"] = action_text
                step_data["params"] = {}
            elif action_text:
                step_data["prompt"] = action_text

            steps.append(step_data)
        return steps

    def _populate_tools_table(self, selected: Optional[List[str]] = None) -> None:
        selected_set = set(selected or DEFAULT_ALLOWED_TOOLS)
        self.tools_table.setRowCount(len(AVAILABLE_AGENT_TOOLS))
        for row, tool in enumerate(AVAILABLE_AGENT_TOOLS):
            enable_item = QTableWidgetItem()
            enable_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            enable_item.setCheckState(
                Qt.CheckState.Checked if tool["id"] in selected_set else Qt.CheckState.Unchecked
            )
            self.tools_table.setItem(row, 0, enable_item)

            name_item = QTableWidgetItem(f"{tool['name']} ({tool['risk']})")
            self.tools_table.setItem(row, 1, name_item)

            desc_item = QTableWidgetItem(tool["description"])
            self.tools_table.setItem(row, 2, desc_item)

    def _collect_selected_tools(self) -> List[str]:
        tools: List[str] = []
        for row, tool in enumerate(AVAILABLE_AGENT_TOOLS):
            item = self.tools_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                tools.append(tool["id"])
        return tools

    def _get_selected_model(self) -> str:
        data = self.model_combo.currentData()
        if data:
            return data
        return self.model_combo.currentText().strip()

    def _set_model_value(self, value: str) -> None:
        if not value:
            if self.model_combo.isEditable():
                self.model_combo.lineEdit().clear()
            self.model_combo.setCurrentIndex(-1)
            return
        idx = self.model_combo.findData(value)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            if self.model_combo.isEditable():
                self.model_combo.lineEdit().setText(value)

    def _on_provider_changed(self, provider: str) -> None:
        """Provider改变时刷新模型下拉/提示"""
        current_value = self._get_selected_model()
        provider_key = None if provider == "auto" else provider
        models = self.orchestrator.provider_manager.get_configured_models(provider_key)

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        if models:
            for item in models:
                if isinstance(item, dict):
                    code = item.get("code") or item.get("name")
                    display = item.get("name", code)
                    if item.get("name") and code:
                        display = f"{item['name']} ({code})"
                    self.model_combo.addItem(display, code)
                else:
                    self.model_combo.addItem(str(item), str(item))
        elif provider_key:
            fallback = self.orchestrator.provider_manager.get_default_model(provider_key)
            if fallback:
                self.model_combo.addItem(fallback, fallback)
        self.model_combo.blockSignals(False)

        placeholder = "如: qwen-plus"
        if models:
            placeholder = "选择或输入模型"
        if self.model_combo.isEditable():
            self.model_combo.lineEdit().setPlaceholderText(placeholder)

        if current_value:
            self._set_model_value(current_value)
        elif models:
            # 默认使用首个模型
            first_data = self.model_combo.currentData()
            if not first_data and self.model_combo.count() > 0:
                self.model_combo.setCurrentIndex(0)
