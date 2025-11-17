"""主窗口"""

import asyncio
from typing import Any, Dict, Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QLabel,
    QComboBox,
    QStatusBar,
    QStackedWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QAction

from .widgets.chat_widget import ChatWidget
from .widgets.sidebar import SidebarWidget
from .widgets.tools_panel import ToolsPanel
from .widgets.tools_page import ToolsPage
from .widgets.settings_dialog import SettingsDialog
from .widgets.settings_page import SettingsPage
from .widgets.models_page import ModelsPage
from .widgets.agents_page import AgentsPage
from .widgets.jobs_page import JobsPage
from .widgets.automation_page import AutomationPage
from .widgets.connector_page import ConnectorPage
from .widgets.knowledge_page import KnowledgeBasePage
from .widgets.sessions_page import SessionsPage
from .widgets.assistants_page import AssistantsPage
from .widgets.logs_page import LogsPage
from .widgets.approval_dialog import ApprovalDialog

from yfai.security.guard import ApprovalRequest, ApprovalResult, ApprovalStatus


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, orchestrator, config_manager):
        super().__init__()
        self.orchestrator = orchestrator
        self.config_manager = config_manager
        self.config = config_manager.get_all()
        self._assistant_cache: Dict[str, Dict[str, Any]] = {}
        self.active_assistant: Optional[Dict[str, Any]] = None

        self._init_ui()
        self._connect_signals()
        self._load_settings()
        self._setup_approval_callback()

    def _init_ui(self) -> None:
        """初始化UI"""
        # 设置窗口属性
        ui_config = self.config.get("ui", {})
        window_width = ui_config.get("window_width", 1400)
        window_height = ui_config.get("window_height", 900)

        self.setWindowTitle("YFAI - 本地对话式控制台")
        self.resize(window_width, window_height)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧边栏
        self.sidebar = SidebarWidget(self.orchestrator)
        splitter.addWidget(self.sidebar)

        # 中间页面堆栈
        self.page_stack = QStackedWidget()

        # 初始化所有页面
        self.chat_widget = ChatWidget(self.orchestrator)
        self.agents_page = AgentsPage(self.orchestrator)
        self.jobs_page = JobsPage(self.orchestrator)
        self.automation_page = AutomationPage(self.orchestrator)
        self.connectors_page = ConnectorPage(self.orchestrator)
        self.knowledge_page = KnowledgeBasePage(self.orchestrator)
        self.sessions_page = SessionsPage(self.orchestrator)
        self.assistants_page = AssistantsPage(self.orchestrator)
        self.logs_page = LogsPage(self.orchestrator)

        # 系统类页面
        self.models_page = ModelsPage(self.orchestrator, self.config_manager)
        self.tools_page = ToolsPage(self.orchestrator, self.config_manager)
        self.settings_page = SettingsPage(self.orchestrator, self.config_manager)

        # 页面映射表
        self.pages = {
            "chat": self.chat_widget,
            "agents": self.agents_page,
            "jobs": self.jobs_page,
            "automation": self.automation_page,
            "connectors": self.connectors_page,
            "knowledge": self.knowledge_page,
            "sessions": self.sessions_page,
            "assistants": self.assistants_page,
            "logs": self.logs_page,
            "models": self.models_page,
            "tools": self.tools_page,
            "settings": self.settings_page,
        }

        # 添加所有页面到堆栈
        for page in self.pages.values():
            self.page_stack.addWidget(page)

        # 默认显示聊天页面
        self.page_stack.setCurrentWidget(self.chat_widget)

        splitter.addWidget(self.page_stack)

        # 右侧工具面板(可折叠)
        self.tools_panel = ToolsPanel(self.orchestrator)
        self.tools_panel.setVisible(False)
        splitter.addWidget(self.tools_panel)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)  # 侧边栏
        splitter.setStretchFactor(1, 4)  # 页面堆栈
        splitter.setStretchFactor(2, 1)  # 工具面板

        main_layout.addWidget(splitter)

        # 创建菜单栏
        self._create_menu_bar()

        # 创建工具栏
        self._create_toolbar()
        self._populate_assistant_combo()

        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")

    def _create_menu_bar(self) -> None:
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        new_action = QAction("新建对话(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.chat_widget.new_session)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        toggle_tools_action = QAction("工具面板(&T)", self)
        toggle_tools_action.setShortcut("Ctrl+T")
        toggle_tools_action.setCheckable(True)
        toggle_tools_action.triggered.connect(self._toggle_tools_panel)
        view_menu.addAction(toggle_tools_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")

        settings_action = QAction("偏好设置(&P)", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        settings_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self) -> None:
        """创建工具栏"""
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)

        # 新建对话按钮
        new_btn = QPushButton("新建对话")
        new_btn.clicked.connect(self.chat_widget.new_session)
        toolbar.addWidget(new_btn)

        toolbar.addSeparator()

        # Provider选择
        toolbar.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["百炼(DashScope)", "Ollama", "自动"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        toolbar.addWidget(self.provider_combo)

        toolbar.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.model_combo.lineEdit().editingFinished.connect(self._on_model_changed)
        toolbar.addWidget(self.model_combo)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel("助手:"))
        self.assistant_combo = QComboBox()
        self.assistant_combo.addItem("未选择", "")
        self.assistant_combo.currentIndexChanged.connect(self._on_assistant_changed)
        toolbar.addWidget(self.assistant_combo)

        toolbar.addSeparator()

        # 健康检查按钮
        health_btn = QPushButton("健康检查")
        health_btn.clicked.connect(self._run_health_check)
        toolbar.addWidget(health_btn)

    def _connect_signals(self) -> None:
        """连接信号"""
        # 侧边栏信号
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.assistants_page.assistant_selected.connect(self._on_assistant_requested)
        self.assistants_page.assistants_updated.connect(self._populate_assistant_combo)
        self.sessions_page.session_resume_requested.connect(self._on_session_resume)

        # 聊天组件信号
        self.chat_widget.status_changed.connect(self.statusBar.showMessage)
        self.settings_page.settings_saved.connect(self._on_config_saved)
        self.models_page.config_updated.connect(self._on_config_saved)

    def _load_settings(self) -> None:
        """加载设置"""
        # 设置默认Provider
        default_provider = self.config.get("app", {}).get("default_provider", "bailian")
        if default_provider == "bailian":
            self.provider_combo.setCurrentText("百炼(DashScope)")
        elif default_provider == "ollama":
            self.provider_combo.setCurrentText("Ollama")
        else:
            self.provider_combo.setCurrentText("自动")
        self._populate_model_combo(self.chat_widget.current_provider or default_provider)
        self._populate_assistant_combo()
        self._update_model_badge()

    def _toggle_tools_panel(self, checked: bool) -> None:
        """切换工具面板显示"""
        self.tools_panel.setVisible(checked)

    def _show_settings(self) -> None:
        """显示设置对话框"""
        dialog = SettingsDialog(self.orchestrator, self.config_manager, self)
        if dialog.exec():
            if dialog.saved_config:
                self._on_config_saved(dialog.saved_config)

    def _show_about(self) -> None:
        """显示关于对话框"""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "关于 YFAI",
            "YFAI - 本地对话式控制台\n\n"
            "版本: 0.1.0\n"
            "统一接入百炼与Ollama\n"
            "MCP Client集成与本地控制能力\n\n"
            "Copyright © 2025 YFAI Team",
        )

    def _on_provider_changed(self, text: str) -> None:
        """Provider改变"""
        if text == "百炼(DashScope)":
            self.chat_widget.current_provider = "bailian"
        elif text == "Ollama":
            self.chat_widget.current_provider = "ollama"
        else:
            self.chat_widget.current_provider = None

        self.statusBar.showMessage(f"已切换到: {text}")
        provider_key = self.chat_widget.current_provider or self.config.get("app", {}).get("default_provider", "bailian")
        self._populate_model_combo(provider_key)
        self._update_model_badge()
        self._persist_toolbar_selection()

    def _on_model_changed(self, *args) -> None:
        """模型切换"""
        current_data = self.model_combo.currentData()
        if current_data:
            self.chat_widget.current_model = current_data
        else:
            self.chat_widget.current_model = self.model_combo.currentText().strip() or None
        if self.chat_widget.current_model:
            self.statusBar.showMessage(f"使用模型: {self.chat_widget.current_model}")
        elif not current_data:
            self.chat_widget.current_model = None
        self._update_model_badge()
        self._persist_toolbar_selection()

    def _populate_assistant_combo(self) -> None:
        """刷新助手下拉"""
        if not hasattr(self, "assistant_combo"):
            return

        current_id = self.active_assistant.get("id") if self.active_assistant else None
        self.assistant_combo.blockSignals(True)
        self.assistant_combo.clear()
        self.assistant_combo.addItem("未选择", "")
        self._assistant_cache = {}

        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Assistant

                assistants = (
                    db_session.query(Assistant)
                    .order_by(Assistant.created_at.desc())
                    .all()
                )
                for assistant in assistants:
                    assistant_dict = assistant.to_dict()
                    self._assistant_cache[assistant.id] = assistant_dict
                    subtitle = assistant.provider or "-"
                    display = f"{assistant.name} ({subtitle})"
                    self.assistant_combo.addItem(display, assistant.id)
        except Exception:
            pass

        if current_id:
            idx = self.assistant_combo.findData(current_id)
            if idx >= 0:
                self.assistant_combo.setCurrentIndex(idx)
            else:
                self.assistant_combo.setCurrentIndex(0)
        else:
            self.assistant_combo.setCurrentIndex(0)

        self.assistant_combo.blockSignals(False)

    def _on_assistant_changed(self, index: int) -> None:
        """来自工具栏的助手切换"""
        if index < 0:
            return
        assistant_id = self.assistant_combo.currentData()
        assistant = self._assistant_cache.get(assistant_id)

        # 如果选择了助手，检查是否有该助手的最近会话
        reset_session = True
        if assistant_id:
            recent_session = self._find_recent_assistant_session(assistant_id)
            if recent_session:
                # 提示用户是否继续最近的会话
                reply = QMessageBox.question(
                    self,
                    "继续会话",
                    f"找到该助手最近的会话「{recent_session['title']}」\n是否继续该会话？\n\n选择「否」将创建新会话。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # 继续旧会话
                    self._on_session_resume(recent_session['id'])
                    return

        self._activate_assistant(assistant, focus_chat=False, reset_session=reset_session)

    def _on_assistant_requested(self, assistant: Dict[str, Any]) -> None:
        """助手管理页请求使用某个助手"""
        assistant_id = assistant.get("id")
        if assistant_id:
            idx = self.assistant_combo.findData(assistant_id)
            if idx >= 0:
                self.assistant_combo.blockSignals(True)
                self.assistant_combo.setCurrentIndex(idx)
                self.assistant_combo.blockSignals(False)
        self._activate_assistant(assistant, focus_chat=True, reset_session=True)

    def _activate_assistant(
        self,
        assistant: Optional[Dict[str, Any]],
        focus_chat: bool,
        reset_session: bool = True,
    ) -> None:
        """同步聊天窗口/工具栏的助手状态"""
        self.active_assistant = assistant
        self.chat_widget.set_active_assistant(assistant)

        if not assistant:
            if focus_chat:
                self.statusBar.showMessage("已清空助手，继续自由对话")
            return

        name = assistant.get("name") or "助手"
        self.statusBar.showMessage(f"已切换助手: {name}")

        provider_key = assistant.get("provider")
        target_text = None
        if provider_key == "bailian":
            target_text = "百炼(DashScope)"
        elif provider_key == "ollama":
            target_text = "Ollama"
        elif provider_key == "auto":
            target_text = "自动"

        if target_text and self.provider_combo.currentText() != target_text:
            self.provider_combo.setCurrentText(target_text)

        model_value = assistant.get("model")
        if model_value:
            idx = self.model_combo.findText(model_value)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.setEditText(model_value)
            self.chat_widget.current_model = model_value

        if focus_chat:
            self._on_page_changed("chat")

        if reset_session and assistant:
            self.chat_widget.new_session()

    def _update_model_badge(self) -> None:
        """同步聊天组件中的模型显示"""
        provider_label = self.provider_combo.currentText()
        model_text = self.chat_widget.current_model or self.model_combo.currentText().strip()
        self.chat_widget.set_active_model(provider_label, model_text)

    def _on_session_resume(self, session_id: str) -> None:
        """从会话列表恢复对话"""
        from yfai.store.db import Session as DbSession, Message

        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                session = db_session.query(DbSession).filter_by(id=session_id).first()
                if not session:
                    QMessageBox.warning(self, "提示", "未找到该会话")
                    return

                messages = (
                    db_session.query(Message)
                    .filter(Message.session_id == session_id)
                    .order_by(Message.created_at)
                    .all()
                )

                assistant_dict = session.assistant.to_dict() if session.assistant else None
                history = [
                    {"role": msg.role, "content": msg.content, "provider": msg.provider, "model": msg.model}
                    for msg in messages
                ]

                provider_name = assistant_dict.get("provider") if assistant_dict else None
                model_name = assistant_dict.get("model") if assistant_dict else None

                if not provider_name:
                    provider_name = next(
                        (msg.provider for msg in reversed(messages) if msg.role == "assistant" and msg.provider),
                        None,
                    )
                if not model_name:
                    model_name = next(
                        (msg.model for msg in reversed(messages) if msg.role == "assistant" and msg.model),
                        None,
                    )

            if assistant_dict:
                self._activate_assistant(assistant_dict, focus_chat=False, reset_session=False)

            self._apply_session_provider_model(provider_name, model_name)
            self.chat_widget.load_session(session_id, history, assistant=assistant_dict)
            self._on_page_changed("chat")
            self.statusBar.showMessage(f"已加载会话: {session.title}")
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"加载会话失败: {exc}")

    def _find_recent_assistant_session(self, assistant_id: str) -> Optional[Dict[str, Any]]:
        """查找助手的最近会话

        Args:
            assistant_id: 助手ID

        Returns:
            最近的会话信息，如果没有则返回 None
        """
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Session as DbSession
                from datetime import datetime, timedelta

                # 查找该助手最近7天内的会话
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                session = (
                    db_session.query(DbSession)
                    .filter(DbSession.assistant_id == assistant_id)
                    .filter(DbSession.updated_at >= cutoff_time)
                    .order_by(DbSession.updated_at.desc())
                    .first()
                )

                if session:
                    return {
                        'id': session.id,
                        'title': session.title,
                        'updated_at': session.updated_at
                    }
        except Exception:
            pass

        return None

    def _apply_session_provider_model(self, provider_name: Optional[str], model_name: Optional[str]) -> None:
        """根据会话记录更新当前 Provider/模型"""
        if provider_name:
            display = {
                "bailian": "百炼(DashScope)",
                "ollama": "Ollama",
                "auto": "自动",
            }.get(provider_name, provider_name)
            existing = {self.provider_combo.itemText(i) for i in range(self.provider_combo.count())}
            if display not in existing:
                self.provider_combo.addItem(display)
            if self.provider_combo.currentText() != display:
                self.provider_combo.setCurrentText(display)
            self.chat_widget.current_provider = provider_name

        if model_name:
            idx = self.model_combo.findText(model_name)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.setEditText(model_name)
            self.chat_widget.current_model = model_name

        self._update_model_badge()
        self._persist_toolbar_selection()

    def _persist_toolbar_selection(self) -> None:
        """将当前 provider/model 写入配置文件"""
        provider_key = self.chat_widget.current_provider or "auto"
        model_value = self.chat_widget.current_model or self.model_combo.currentText().strip() or None

        try:
            self.config_manager.set("app.default_provider", provider_key)

            if provider_key in ("bailian", "ollama") and model_value:
                self.config_manager.set(f"providers.{provider_key}.default_model", model_value)

            self.config_manager.save()
            self.config = self.config_manager.get_all()
            self.orchestrator.update_config(self.config)
        except Exception as exc:
            QMessageBox.warning(self, "配置保存失败", str(exc))

    def _create_placeholder_page(self, title: str) -> QWidget:
        """创建占位页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel(f"📋 {title}\n\n该功能正在开发中...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16pt; color: #666;")

        layout.addWidget(label)
        return widget

    def _on_page_changed(self, page: str) -> None:
        """页面改变"""
        if page in self.pages:
            self.page_stack.setCurrentWidget(self.pages[page])

            # 更新状态栏
            page_names = {
                "chat": "对话",
                "agents": "智能体",
                "jobs": "运行记录",
                "automation": "自动化管理",
                "connectors": "连接器管理",
                "knowledge": "知识库",
                "sessions": "会话管理",
                "assistants": "助手管理",
                "logs": "日志查看",
                "models": "模型管理",
                "tools": "工具管理",
                "settings": "系统设置",
            }
            page_name = page_names.get(page, page)
            self.statusBar.showMessage(f"当前页面: {page_name}")
        else:
            self.statusBar.showMessage(f"⚠️ 页面 '{page}' 不存在")

    def _run_health_check(self) -> None:
        """运行健康检查"""
        self.statusBar.showMessage("正在进行健康检查...")

        async def check():
            result = await self.orchestrator.health_check()
            providers = result.get("providers", {})

            status_text = []
            for name, healthy in providers.items():
                status = "正常" if healthy else "异常"
                status_text.append(f"{name}: {status}")

            self.statusBar.showMessage(" | ".join(status_text))

        asyncio.create_task(check())

    def _setup_approval_callback(self) -> None:
        """设置审批回调函数"""
        def approval_callback(request: ApprovalRequest) -> ApprovalResult:
            """审批回调函数

            在主线程中显示审批对话框，并返回用户的审批决策
            """
            # 显示审批对话框
            dialog = ApprovalDialog(request, self)
            result_code = dialog.exec()

            # 处理结果
            if result_code == ApprovalDialog.APPROVED_ONCE:
                return ApprovalResult(
                    request_id=request.id,
                    status=ApprovalStatus.APPROVED,
                    approved_by="user",
                    reason="仅此一次允许",
                )
            elif result_code == ApprovalDialog.APPROVED_ALWAYS:
                # TODO: 保存到白名单/永久允许规则
                return ApprovalResult(
                    request_id=request.id,
                    status=ApprovalStatus.APPROVED,
                    approved_by="user",
                    reason="永久允许",
                )
            else:
                return ApprovalResult(
                    request_id=request.id,
                    status=ApprovalStatus.REJECTED,
                    approved_by="user",
                    reason="用户拒绝执行",
                )

        # 设置回调函数到 security_guard
        self.orchestrator.security_guard.set_approval_callback(approval_callback)

    def _on_config_saved(self, new_config: Dict[str, Any]) -> None:
        """配置保存后更新运行时依赖"""
        self.config = new_config
        self.settings_page.reload_config(new_config)
        self.tools_page.refresh()

        # 更新Orchestrator依赖
        self.orchestrator.update_config(new_config)
        self._load_settings()

    def _populate_model_combo(self, provider_key: Optional[str]) -> None:
        """根据Provider刷新模型下拉"""
        if not hasattr(self, "model_combo"):
            return

        models = self.orchestrator.provider_manager.get_configured_models(provider_key)
        current_value = self.chat_widget.current_model

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
        default_model = self.orchestrator.provider_manager.get_default_model(provider_key)
        if not self.model_combo.count() and default_model:
            self.model_combo.addItem(default_model, default_model)
        self.model_combo.blockSignals(False)

        # 更新选择
        if current_value:
            idx = self.model_combo.findData(current_value)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.chat_widget.current_model = current_value
                self.model_combo.setEditText(current_value)
        elif self.model_combo.count():
            self.model_combo.setCurrentIndex(0)
            self.chat_widget.current_model = self.model_combo.currentData()
        else:
            self.model_combo.setEditText("")
            self.chat_widget.current_model = None

    def closeEvent(self, event):
        """关闭窗口事件处理"""
        # 取消所有活动的异步任务
        try:
            self.chat_widget.cancel_all_tasks()
        except Exception as e:
            import logging
            logging.error(f"取消任务失败: {e}")

        # 接受关闭事件
        event.accept()

