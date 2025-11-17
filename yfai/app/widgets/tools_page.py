"""工具管理页面"""

from __future__ import annotations

from typing import Dict, List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTabWidget,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
)
from PyQt6.QtCore import Qt


class ToolsPage(QWidget):
    """展示本地能力与MCP工具的管理页面"""

    def __init__(self, orchestrator, config_manager, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.config_manager = config_manager
        self.local_tools: List[Dict[str, str]] = self._build_local_tools()

        self._init_ui()
        self._populate_local_tools()
        self._load_mcp_servers()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🧰 工具与能力")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("查看内置本地能力、MCP服务器及可用工具")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 本地工具标签页
        local_tab = QWidget()
        local_layout = QVBoxLayout(local_tab)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.local_search = QLineEdit()
        self.local_search.setPlaceholderText("输入名称、ID或描述")
        self.local_search.textChanged.connect(self._filter_local_tools)
        search_layout.addWidget(self.local_search)
        local_layout.addLayout(search_layout)

        self.local_table = QTableWidget()
        self.local_table.setColumnCount(7)
        self.local_table.setHorizontalHeaderLabels([
            "名称", "工具ID", "风险等级", "状态", "调用次数", "成功率", "说明"
        ])
        header = self.local_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.local_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.local_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        local_layout.addWidget(self.local_table)

        # 工具操作按钮
        tool_actions = QHBoxLayout()
        self.toggle_tool_btn = QPushButton("启用/禁用工具")
        self.toggle_tool_btn.clicked.connect(self._toggle_tool_status)
        tool_actions.addWidget(self.toggle_tool_btn)

        self.clear_stats_btn = QPushButton("清除统计")
        self.clear_stats_btn.clicked.connect(self._clear_tool_stats)
        tool_actions.addWidget(self.clear_stats_btn)

        tool_actions.addStretch()
        local_layout.addLayout(tool_actions)

        # 工具状态存储（tool_id -> enabled）
        self.tool_enabled_status: Dict[str, bool] = {}

        self.tabs.addTab(local_tab, "本地能力")

        # MCP工具标签页
        mcp_tab = QWidget()
        mcp_layout = QVBoxLayout(mcp_tab)

        header_layout = QHBoxLayout()
        self.mcp_stats_label = QLabel("未加载")
        header_layout.addWidget(self.mcp_stats_label)
        header_layout.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._load_mcp_servers)
        header_layout.addWidget(refresh_btn)
        mcp_layout.addLayout(header_layout)

        self.mcp_table = QTableWidget()
        self.mcp_table.setColumnCount(5)
        self.mcp_table.setHorizontalHeaderLabels([
            "名称",
            "Endpoint",
            "状态",
            "工具数量",
            "描述",
        ])
        mcp_header = self.mcp_table.horizontalHeader()
        mcp_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        mcp_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        mcp_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        mcp_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        mcp_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.mcp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.mcp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        mcp_layout.addWidget(self.mcp_table)

        self.tabs.addTab(mcp_tab, "MCP 工具")

    def refresh(self) -> None:
        """Public method to reload data when config changes."""
        self.local_tools = self._build_local_tools()
        self._populate_local_tools()
        self._load_mcp_servers()

    # Local tools -----------------------------------------------------
    def _build_local_tools(self) -> List[Dict[str, str]]:
        return [
            {
                "name": "读取文件",
                "id": "fs.read_file",
                "risk": "低",
                "desc": "读取白名单目录内的文本/二进制文件",
            },
            {
                "name": "写入文件",
                "id": "fs.write_file",
                "risk": "中",
                "desc": "写入文件内容, 触发安全审批",
            },
            {
                "name": "列出目录",
                "id": "fs.list_directory",
                "risk": "低",
                "desc": "查看目标目录下的文件与子目录",
            },
            {
                "name": "搜索文件",
                "id": "fs.search",
                "risk": "低",
                "desc": "按名称/内容检索文件",
            },
            {
                "name": "执行Shell命令",
                "id": "shell.execute",
                "risk": "中",
                "desc": "在默认Shell中执行命令, 可配置超时",
            },
            {
                "name": "进程列表",
                "id": "process.list",
                "risk": "低",
                "desc": "查看当前系统进程信息",
            },
            {
                "name": "HTTP请求",
                "id": "net.http_request",
                "risk": "低",
                "desc": "发起HTTP GET/POST请求, 支持自定义Headers",
            },
            {
                "name": "端口检测",
                "id": "net.check_port",
                "risk": "低",
                "desc": "检测远程主机端口联通性",
            },
        ]

    def _populate_local_tools(self) -> None:
        """填充本地工具列表，包含使用统计"""
        # 加载工具启用状态
        self._load_tool_status()

        # 获取工具使用统计
        tool_stats = self._get_tool_statistics()

        self.local_table.setRowCount(len(self.local_tools))
        for row, tool in enumerate(self.local_tools):
            tool_id = tool["id"]

            # 名称
            self.local_table.setItem(row, 0, QTableWidgetItem(tool["name"]))

            # 工具ID
            self.local_table.setItem(row, 1, QTableWidgetItem(tool_id))

            # 风险等级
            risk_item = QTableWidgetItem(tool["risk"])
            if tool["risk"] == "低":
                risk_item.setForeground(Qt.GlobalColor.darkGreen)
            elif tool["risk"] == "中":
                risk_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                risk_item.setForeground(Qt.GlobalColor.red)
            self.local_table.setItem(row, 2, risk_item)

            # 状态（启用/禁用）
            enabled = self.tool_enabled_status.get(tool_id, True)
            status_text = "✅ 启用" if enabled else "❌ 禁用"
            status_item = QTableWidgetItem(status_text)
            if enabled:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            self.local_table.setItem(row, 3, status_item)

            # 统计数据
            stats = tool_stats.get(tool_id, {"total": 0, "success": 0})
            total_calls = stats["total"]
            success_calls = stats["success"]
            success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0

            # 调用次数
            self.local_table.setItem(row, 4, QTableWidgetItem(str(total_calls)))

            # 成功率
            success_rate_text = f"{success_rate:.1f}%" if total_calls > 0 else "N/A"
            self.local_table.setItem(row, 5, QTableWidgetItem(success_rate_text))

            # 说明
            self.local_table.setItem(row, 6, QTableWidgetItem(tool["desc"]))

    def _get_tool_statistics(self) -> Dict[str, Dict[str, int]]:
        """从数据库获取工具使用统计

        Returns:
            {tool_name: {"total": count, "success": count}}
        """
        stats = {}
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import ToolCall
                from sqlalchemy import func

                # 查询每个工具的总调用次数和成功次数
                results = db_session.query(
                    ToolCall.tool_name,
                    func.count(ToolCall.id).label("total"),
                    func.sum(func.case((ToolCall.status == "success", 1), else_=0)).label("success")
                ).group_by(ToolCall.tool_name).all()

                for tool_name, total, success in results:
                    stats[tool_name] = {
                        "total": total or 0,
                        "success": success or 0,
                    }
        except Exception as e:
            print(f"获取工具统计失败: {e}")

        return stats

    def _load_tool_status(self) -> None:
        """从数据库加载工具启用状态"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import KVStore
                import json

                # 从 KVStore 读取工具状态
                kv = db_session.query(KVStore).filter_by(
                    namespace="tools",
                    key="enabled_status"
                ).first()

                if kv:
                    self.tool_enabled_status = json.loads(kv.value)
                else:
                    # 默认所有工具启用
                    self.tool_enabled_status = {}
        except Exception:
            self.tool_enabled_status = {}

    def _save_tool_status(self) -> None:
        """保存工具启用状态到数据库"""
        try:
            import json
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import KVStore
                from datetime import datetime

                kv = db_session.query(KVStore).filter_by(
                    namespace="tools",
                    key="enabled_status"
                ).first()

                if kv:
                    kv.value = json.dumps(self.tool_enabled_status)
                    kv.updated_at = datetime.utcnow()
                else:
                    kv = KVStore(
                        namespace="tools",
                        key="enabled_status",
                        value=json.dumps(self.tool_enabled_status)
                    )
                    db_session.add(kv)

                db_session.commit()
        except Exception as e:
            print(f"保存工具状态失败: {e}")

    def _toggle_tool_status(self) -> None:
        """切换选中工具的启用/禁用状态"""
        from PyQt6.QtWidgets import QMessageBox

        current_row = self.local_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择一个工具")
            return

        tool_id_item = self.local_table.item(current_row, 1)
        if not tool_id_item:
            return

        tool_id = tool_id_item.text()
        current_status = self.tool_enabled_status.get(tool_id, True)
        new_status = not current_status

        self.tool_enabled_status[tool_id] = new_status
        self._save_tool_status()
        self._populate_local_tools()

        status_text = "启用" if new_status else "禁用"
        QMessageBox.information(self, "成功", f"工具 {tool_id} 已{status_text}")

    def _clear_tool_stats(self) -> None:
        """清除工具统计数据"""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有工具的调用统计吗？\n注意：此操作不会删除审计日志。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import ToolCall

                    # 这里不真正删除记录，只是重置统计（可以考虑添加一个统计重置时间戳）
                    # 实际上统计是实时计算的，所以这个功能可以改为"归档旧记录"
                    QMessageBox.information(
                        self,
                        "提示",
                        "统计数据基于 ToolCall 记录实时计算\n如需清理，请前往日志页面清理旧记录"
                    )
            except Exception as e:
                QMessageBox.critical(self, "错误", f"操作失败: {e}")

    def _filter_local_tools(self, text: str) -> None:
        keyword = text.lower().strip()
        for row in range(self.local_table.rowCount()):
            visible = True
            if keyword:
                row_text = " ".join(
                    self.local_table.item(row, col).text().lower()
                    for col in range(self.local_table.columnCount())
                    if self.local_table.item(row, col)
                )
                visible = keyword in row_text
            self.local_table.setRowHidden(row, not visible)

    # MCP servers -----------------------------------------------------
    def _load_mcp_servers(self) -> None:
        servers = []
        try:
            servers = self.orchestrator.mcp_registry.list_servers()
        except Exception:
            # Registry 可能未配置
            pass

        self.mcp_table.setRowCount(len(servers))
        total_tools = 0
        enabled = 0

        for row, server in enumerate(servers):
            self.mcp_table.setItem(row, 0, QTableWidgetItem(server.name))
            self.mcp_table.setItem(row, 1, QTableWidgetItem(server.endpoint))
            status = "启用" if server.enabled else "禁用"
            status_item = QTableWidgetItem(status)
            if server.enabled:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
                enabled += 1
            else:
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            self.mcp_table.setItem(row, 2, status_item)

            tools = server.get_tools()
            total_tools += len(tools)
            self.mcp_table.setItem(row, 3, QTableWidgetItem(str(len(tools))))
            self.mcp_table.setItem(row, 4, QTableWidgetItem(server.description or "-"))

        if servers:
            self.mcp_stats_label.setText(
                f"已配置 {len(servers)} 个服务器, 启用 {enabled} 个, 工具 {total_tools} 个"
            )
        else:
            self.mcp_stats_label.setText("未加载到任何MCP服务器, 请在 configs/McpRegistry.yaml 中配置")
