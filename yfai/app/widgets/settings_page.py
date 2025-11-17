"""Settings page displayed inside the main window."""

import asyncio
from typing import Any, Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
)

from .settings_form import SettingsForm


class SettingsPage(QWidget):
    """System settings management page."""

    settings_saved = pyqtSignal(dict)

    def __init__(self, orchestrator, config_manager, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.config_manager = config_manager

        self._init_ui()
        self.form.refresh_models_btn.clicked.connect(self._refresh_models)
        self._refresh_models()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⚙️ 系统设置")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("配置模型、接口参数、安全策略等运行偏好")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        self.form = SettingsForm(self.config_manager.get_all())
        layout.addWidget(self.form)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    # Public API ------------------------------------------------------
    def reload_config(self, config: Dict[str, Any]) -> None:
        self.form.load_config(config)
        self.status_label.setText("")

    # Slots -----------------------------------------------------------
    def _on_reset(self) -> None:
        self.form.load_config(self.config_manager.get_all())
        self.status_label.setText("已恢复到当前配置")

    def _on_save(self) -> None:
        try:
            values = self.form.collect_settings()
            self._persist(values)
        except Exception as exc:
            self.status_label.setStyleSheet("color: #d63031;")
            self.status_label.setText(f"保存失败: {exc}")
            return

        new_config = self.config_manager.get_all()
        self.status_label.setStyleSheet("color: #2ecc71;")
        self.status_label.setText("设置已保存")
        self.settings_saved.emit(new_config)

    def _persist(self, values: Dict[str, Any]) -> None:
        for key, value in values.get("app", {}).items():
            self.config_manager.set(f"app.{key}", value)

        for provider, cfg in values.get("providers", {}).items():
            for key, value in cfg.items():
                self.config_manager.set(f"providers.{provider}.{key}", value)

        for key, value in values.get("security", {}).items():
            self.config_manager.set(f"security.{key}", value)

        self.config_manager.save()

    def _refresh_models(self) -> None:
        self.form.refresh_models_btn.setEnabled(False)
        self.form.models_status_label.setText("正在刷新模型列表…")

        async def fetch() -> None:
            try:
                models = await self.orchestrator.provider_manager.list_all_models()
                self.form.set_available_models(models)
            except Exception as exc:
                self.form.models_status_label.setText(f"加载失败: {exc}")
            else:
                if not models:
                    self.form.models_status_label.setText("未能读取到模型信息")
            finally:
                self.form.refresh_models_btn.setEnabled(True)

        loop = asyncio.get_event_loop()
        loop.create_task(fetch())
