"""智能体管理页面"""

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
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import asyncio


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

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_agents)
        title_layout.addWidget(refresh_btn)

        layout.addLayout(title_layout)

        # 智能体列表
        self.agent_list = QListWidget()
        self.agent_list.itemClicked.connect(self._on_agent_selected)
        layout.addWidget(self.agent_list)

        # 运行控制区
        run_layout = QHBoxLayout()
        run_label = QLabel("目标:")
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("输入智能体要完成的目标...")
        run_btn = QPushButton("▶ 运行")
        run_btn.clicked.connect(self._on_run_agent)
        run_layout.addWidget(run_label)
        run_layout.addWidget(self.goal_input)
        run_layout.addWidget(run_btn)
        layout.addLayout(run_layout)

        self.setLayout(layout)

        # 加载智能体列表
        self._load_agents()

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

    def _on_create_agent(self):
        """创建新智能体"""
        dialog = AgentEditDialog(self.orchestrator, parent=self)
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
        QMessageBox.information(self, "成功", "智能体已开始执行,请查看运行记录页面")

    async def _run_agent_async(self, agent_id: str, goal: str):
        """异步运行智能体"""
        try:
            result = await self.orchestrator.run_agent(agent_id, goal)
            print(f"Agent run completed: {result}")
        except Exception as e:
            print(f"Agent run failed: {e}")


class AgentEditDialog(QDialog):
    """智能体编辑对话框"""

    def __init__(self, orchestrator, agent_id=None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.agent_id = agent_id
        self.setWindowTitle("新建智能体" if not agent_id else "编辑智能体")
        self.resize(600, 500)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 表单
        form = QFormLayout()

        self.name_input = QLineEdit()
        form.addRow("名称:", self.name_input)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        form.addRow("描述:", self.desc_input)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("输入系统提示词...")
        form.addRow("系统提示词:", self.prompt_input)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["bailian", "ollama", "auto"])
        form.addRow("Provider:", self.provider_combo)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("如: qwen-plus, qwen2.5-coder")
        form.addRow("模型:", self.model_input)

        self.max_steps_spin = QSpinBox()
        self.max_steps_spin.setMinimum(1)
        self.max_steps_spin.setMaximum(100)
        self.max_steps_spin.setValue(10)
        form.addRow("最大步骤数:", self.max_steps_spin)

        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        form.addRow("启用:", self.enabled_check)

        layout.addLayout(form)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _on_accept(self):
        """确认创建/编辑"""
        import json
        import uuid

        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入智能体名称")
            return

        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "错误", "请输入系统提示词")
            return

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
                agent.default_model = self.model_input.text().strip()
                agent.max_steps = self.max_steps_spin.value()
                agent.is_enabled = self.enabled_check.isChecked()
                agent.allowed_tools = json.dumps([
                    "shell.execute",
                    "fs.read_file",
                    "fs.write_file",
                    "fs.list_directory",
                    "process.list",
                    "process.info",
                    "net.http_request",
                    "net.check_port",
                    "net.get_local_ip",
                ])

                if not self.agent_id:
                    db_session.add(agent)

                db_session.commit()

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
