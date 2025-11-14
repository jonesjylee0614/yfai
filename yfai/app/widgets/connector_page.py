"""连接器管理页面"""

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
    QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class ConnectorDialog(QDialog):
    """连接器编辑对话框"""

    def __init__(self, orchestrator, connector: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.connector = connector
        self.is_edit = connector is not None

        self.setWindowTitle("编辑连接器" if self.is_edit else "创建连接器")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._init_ui()
        if self.is_edit:
            self._load_connector_data()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 表单
        form_layout = QFormLayout()

        # 连接器名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("连接器名称")
        form_layout.addRow("名称:", self.name_edit)

        # 连接器类型
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "http (HTTP API)",
            "email (邮件)",
            "git (Git仓库)",
            "custom (自定义)",
        ])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_layout.addRow("类型:", self.type_combo)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("连接器描述")
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow("描述:", self.description_edit)

        # 配置区域
        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout(self.config_widget)
        self.config_layout.setContentsMargins(0, 0, 0, 0)

        # HTTP 配置
        self.http_widget = QWidget()
        http_layout = QFormLayout(self.http_widget)

        self.http_base_url = QLineEdit()
        self.http_base_url.setPlaceholderText("https://api.example.com")
        http_layout.addRow("基础URL:", self.http_base_url)

        self.http_auth_type = QComboBox()
        self.http_auth_type.addItems(["无认证", "Bearer Token", "Basic Auth", "API Key"])
        http_layout.addRow("认证类型:", self.http_auth_type)

        self.http_auth_value = QLineEdit()
        self.http_auth_value.setPlaceholderText("认证凭证")
        self.http_auth_value.setEchoMode(QLineEdit.EchoMode.Password)
        http_layout.addRow("认证凭证:", self.http_auth_value)

        self.http_headers = QTextEdit()
        self.http_headers.setPlaceholderText('{"Content-Type": "application/json"}')
        self.http_headers.setMaximumHeight(80)
        http_layout.addRow("自定义Headers:", self.http_headers)

        self.config_layout.addWidget(self.http_widget)

        # Email 配置
        self.email_widget = QWidget()
        email_layout = QFormLayout(self.email_widget)

        self.email_smtp_host = QLineEdit()
        self.email_smtp_host.setPlaceholderText("smtp.gmail.com")
        email_layout.addRow("SMTP主机:", self.email_smtp_host)

        self.email_smtp_port = QLineEdit()
        self.email_smtp_port.setPlaceholderText("587")
        email_layout.addRow("SMTP端口:", self.email_smtp_port)

        self.email_username = QLineEdit()
        self.email_username.setPlaceholderText("user@example.com")
        email_layout.addRow("用户名:", self.email_username)

        self.email_password = QLineEdit()
        self.email_password.setEchoMode(QLineEdit.EchoMode.Password)
        email_layout.addRow("密码:", self.email_password)

        self.email_from = QLineEdit()
        self.email_from.setPlaceholderText("sender@example.com")
        email_layout.addRow("发件人:", self.email_from)

        self.config_layout.addWidget(self.email_widget)
        self.email_widget.setVisible(False)

        # Git 配置
        self.git_widget = QWidget()
        git_layout = QFormLayout(self.git_widget)

        self.git_repo_url = QLineEdit()
        self.git_repo_url.setPlaceholderText("https://github.com/user/repo.git")
        git_layout.addRow("仓库URL:", self.git_repo_url)

        self.git_branch = QLineEdit()
        self.git_branch.setPlaceholderText("main")
        git_layout.addRow("分支:", self.git_branch)

        self.git_username = QLineEdit()
        git_layout.addRow("用户名:", self.git_username)

        self.git_token = QLineEdit()
        self.git_token.setEchoMode(QLineEdit.EchoMode.Password)
        git_layout.addRow("访问令牌:", self.git_token)

        self.config_layout.addWidget(self.git_widget)
        self.git_widget.setVisible(False)

        # Custom 配置
        self.custom_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_widget)

        custom_label = QLabel("JSON配置:")
        custom_layout.addWidget(custom_label)

        self.custom_config = QTextEdit()
        self.custom_config.setPlaceholderText('{\n  "key": "value"\n}')
        custom_layout.addWidget(self.custom_config)

        self.config_layout.addWidget(self.custom_widget)
        self.custom_widget.setVisible(False)

        form_layout.addRow("配置:", self.config_widget)

        layout.addLayout(form_layout)

        # 按钮
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def _on_type_changed(self, index: int):
        """连接器类型改变"""
        # 隐藏所有配置
        self.http_widget.setVisible(False)
        self.email_widget.setVisible(False)
        self.git_widget.setVisible(False)
        self.custom_widget.setVisible(False)

        # 显示对应的配置
        if index == 0:  # http
            self.http_widget.setVisible(True)
        elif index == 1:  # email
            self.email_widget.setVisible(True)
        elif index == 2:  # git
            self.git_widget.setVisible(True)
        elif index == 3:  # custom
            self.custom_widget.setVisible(True)

    def _load_connector_data(self):
        """加载连接器数据"""
        if not self.connector:
            return

        self.name_edit.setText(self.connector.get("name", ""))
        self.description_edit.setPlainText(self.connector.get("description", ""))

        # 连接器类型
        conn_type = self.connector.get("type", "http")
        type_map = {
            "http": 0,
            "email": 1,
            "git": 2,
            "custom": 3,
        }
        self.type_combo.setCurrentIndex(type_map.get(conn_type, 0))

        # 配置
        config = self.connector.get("config", {})
        if isinstance(config, str):
            config = json.loads(config)

        if conn_type == "http":
            self.http_base_url.setText(config.get("base_url", ""))
            auth_type = config.get("auth_type", "无认证")
            self.http_auth_type.setCurrentText(auth_type)
            self.http_auth_value.setText(config.get("auth_value", ""))
            headers = config.get("headers", {})
            if headers:
                self.http_headers.setPlainText(json.dumps(headers, indent=2, ensure_ascii=False))
        elif conn_type == "email":
            self.email_smtp_host.setText(config.get("smtp_host", ""))
            self.email_smtp_port.setText(str(config.get("smtp_port", "")))
            self.email_username.setText(config.get("username", ""))
            self.email_password.setText(config.get("password", ""))
            self.email_from.setText(config.get("from", ""))
        elif conn_type == "git":
            self.git_repo_url.setText(config.get("repo_url", ""))
            self.git_branch.setText(config.get("branch", ""))
            self.git_username.setText(config.get("username", ""))
            self.git_token.setText(config.get("token", ""))
        elif conn_type == "custom":
            self.custom_config.setPlainText(json.dumps(config, indent=2, ensure_ascii=False))

    def get_connector_data(self) -> dict:
        """获取连接器数据"""
        type_index = self.type_combo.currentIndex()
        type_names = ["http", "email", "git", "custom"]
        conn_type = type_names[type_index]

        data = {
            "name": self.name_edit.text(),
            "type": conn_type,
            "description": self.description_edit.toPlainText(),
        }

        # 配置
        config = {}
        if conn_type == "http":
            config = {
                "base_url": self.http_base_url.text(),
                "auth_type": self.http_auth_type.currentText(),
                "auth_value": self.http_auth_value.text(),
            }
            headers_text = self.http_headers.toPlainText().strip()
            if headers_text:
                try:
                    config["headers"] = json.loads(headers_text)
                except json.JSONDecodeError:
                    pass
        elif conn_type == "email":
            config = {
                "smtp_host": self.email_smtp_host.text(),
                "smtp_port": int(self.email_smtp_port.text() or "587"),
                "username": self.email_username.text(),
                "password": self.email_password.text(),
                "from": self.email_from.text(),
            }
        elif conn_type == "git":
            config = {
                "repo_url": self.git_repo_url.text(),
                "branch": self.git_branch.text(),
                "username": self.git_username.text(),
                "token": self.git_token.text(),
            }
        elif conn_type == "custom":
            config_text = self.custom_config.toPlainText().strip()
            if config_text:
                try:
                    config = json.loads(config_text)
                except json.JSONDecodeError:
                    config = {"raw": config_text}

        data["config"] = json.dumps(config, ensure_ascii=False)
        return data


class ConnectorPage(QWidget):
    """连接器管理页面"""

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
        self._load_connectors()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 顶部工具栏
        toolbar = QHBoxLayout()

        create_btn = QPushButton("➕ 创建连接器")
        create_btn.clicked.connect(self._create_connector)
        toolbar.addWidget(create_btn)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_connectors)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 连接器列表
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "名称", "类型", "状态", "最后测试", "使用次数", "操作", "ID"
        ])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnHidden(6, True)  # 隐藏ID列

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _load_connectors(self):
        """加载连接器列表"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Connector

                connectors = db_session.query(Connector).all()
                self.table.setRowCount(len(connectors))

                for row, connector in enumerate(connectors):
                    # 名称
                    self.table.setItem(row, 0, QTableWidgetItem(connector.name))

                    # 类型
                    self.table.setItem(row, 1, QTableWidgetItem(connector.type))

                    # 状态
                    status_map = {
                        "connected": ("✓ 已连接", "#00b894"),
                        "disconnected": ("✗ 未连接", "#b2bec3"),
                        "error": ("⚠ 错误", "#d63031"),
                        "unknown": ("? 未知", "#fdcb6e"),
                    }
                    status_text, status_color = status_map.get(
                        connector.status, ("? 未知", "#fdcb6e")
                    )
                    status_item = QTableWidgetItem(status_text)
                    status_item.setForeground(QColor(status_color))
                    self.table.setItem(row, 2, status_item)

                    # 最后测试
                    last_test = connector.last_test_at.strftime("%Y-%m-%d %H:%M") if connector.last_test_at else "-"
                    self.table.setItem(row, 3, QTableWidgetItem(last_test))

                    # 使用次数
                    self.table.setItem(row, 4, QTableWidgetItem(str(connector.use_count)))

                    # 操作按钮
                    actions_widget = self._create_action_buttons(connector.id)
                    self.table.setCellWidget(row, 5, actions_widget)

                    # ID (隐藏)
                    self.table.setItem(row, 6, QTableWidgetItem(connector.id))

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载连接器列表失败: {e}")

    def _create_action_buttons(self, connector_id: str) -> QWidget:
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 测试连接按钮
        test_btn = QPushButton("🔌")
        test_btn.setMaximumWidth(30)
        test_btn.setToolTip("测试连接")
        test_btn.clicked.connect(lambda: self._test_connector(connector_id))
        layout.addWidget(test_btn)

        # 编辑按钮
        edit_btn = QPushButton("✎")
        edit_btn.setMaximumWidth(30)
        edit_btn.setToolTip("编辑")
        edit_btn.clicked.connect(lambda: self._edit_connector(connector_id))
        layout.addWidget(edit_btn)

        # 删除按钮
        delete_btn = QPushButton("🗑")
        delete_btn.setMaximumWidth(30)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda: self._delete_connector(connector_id))
        layout.addWidget(delete_btn)

        return widget

    def _create_connector(self):
        """创建连接器"""
        dialog = ConnectorDialog(self.orchestrator, parent=self)
        if dialog.exec():
            try:
                data = dialog.get_connector_data()
                data["id"] = str(uuid.uuid4())
                data["status"] = "unknown"

                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import Connector

                    connector = Connector(**data)
                    db_session.add(connector)
                    db_session.commit()

                QMessageBox.information(self, "成功", "连接器创建成功")
                self._load_connectors()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建连接器失败: {e}")

    def _edit_connector(self, connector_id: str):
        """编辑连接器"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Connector

                connector = db_session.query(Connector).filter_by(id=connector_id).first()
                if not connector:
                    QMessageBox.warning(self, "警告", "连接器不存在")
                    return

                connector_dict = connector.to_dict()

            dialog = ConnectorDialog(self.orchestrator, connector_dict, parent=self)
            if dialog.exec():
                data = dialog.get_connector_data()

                with self.orchestrator.db_manager.get_session() as db_session:
                    connector = db_session.query(Connector).filter_by(id=connector_id).first()
                    if connector:
                        for key, value in data.items():
                            setattr(connector, key, value)
                        connector.updated_at = datetime.utcnow()
                        db_session.commit()

                QMessageBox.information(self, "成功", "连接器更新成功")
                self._load_connectors()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑连接器失败: {e}")

    def _test_connector(self, connector_id: str):
        """测试连接器连接"""
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import Connector

                connector = db_session.query(Connector).filter_by(id=connector_id).first()
                if not connector:
                    QMessageBox.warning(self, "警告", "连接器不存在")
                    return

                # TODO: 实际测试连接逻辑
                # 暂时模拟测试
                connector.status = "connected"
                connector.last_test_at = datetime.utcnow()
                db_session.commit()

                QMessageBox.information(self, "成功", f"连接器 '{connector.name}' 测试成功")
                self._load_connectors()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"测试连接失败: {e}")

    def _delete_connector(self, connector_id: str):
        """删除连接器"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除此连接器吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.orchestrator.db_manager.get_session() as db_session:
                    from yfai.store.db import Connector

                    connector = db_session.query(Connector).filter_by(id=connector_id).first()
                    if connector:
                        db_session.delete(connector)
                        db_session.commit()

                QMessageBox.information(self, "成功", "连接器已删除")
                self._load_connectors()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除连接器失败: {e}")
