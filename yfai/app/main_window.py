"""主窗口"""

import asyncio
from typing import Any, Dict

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
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QAction

from .widgets.chat_widget import ChatWidget
from .widgets.sidebar import SidebarWidget
from .widgets.tools_panel import ToolsPanel
from .widgets.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, orchestrator, config: Dict[str, Any]):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config

        self._init_ui()
        self._connect_signals()
        self._load_settings()

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

        # 中间对话区域
        self.chat_widget = ChatWidget(self.orchestrator)
        splitter.addWidget(self.chat_widget)

        # 右侧工具面板(可折叠)
        self.tools_panel = ToolsPanel(self.orchestrator)
        self.tools_panel.setVisible(False)
        splitter.addWidget(self.tools_panel)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)  # 侧边栏
        splitter.setStretchFactor(1, 4)  # 对话区
        splitter.setStretchFactor(2, 1)  # 工具面板

        main_layout.addWidget(splitter)

        # 创建菜单栏
        self._create_menu_bar()

        # 创建工具栏
        self._create_toolbar()

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

        toolbar.addSeparator()

        # 健康检查按钮
        health_btn = QPushButton("健康检查")
        health_btn.clicked.connect(self._run_health_check)
        toolbar.addWidget(health_btn)

    def _connect_signals(self) -> None:
        """连接信号"""
        # 侧边栏信号
        self.sidebar.page_changed.connect(self._on_page_changed)

        # 聊天组件信号
        self.chat_widget.status_changed.connect(self.statusBar.showMessage)

    def _load_settings(self) -> None:
        """加载设置"""
        # 设置默认Provider
        default_provider = self.config.get("app", {}).get("default_provider", "bailian")
        if default_provider == "bailian":
            self.provider_combo.setCurrentText("百炼(DashScope)")
        elif default_provider == "ollama":
            self.provider_combo.setCurrentText("Ollama")

    def _toggle_tools_panel(self, checked: bool) -> None:
        """切换工具面板显示"""
        self.tools_panel.setVisible(checked)

    def _show_settings(self) -> None:
        """显示设置对话框"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # 保存设置
            pass

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

    def _on_page_changed(self, page: str) -> None:
        """页面改变"""
        self.statusBar.showMessage(f"切换到: {page}")

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

