"""设置对话框"""

import asyncio
from typing import Any, Dict

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)

from .settings_form import SettingsForm


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, orchestrator, config_manager, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.config_manager = config_manager
        self.saved_config: Dict[str, Any] | None = None

        self.setWindowTitle("设置")
        self.resize(700, 560)

        layout = QVBoxLayout(self)
        self.form = SettingsForm(config_manager.get_all())
        layout.addWidget(self.form)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.form.refresh_models_btn.clicked.connect(self._refresh_models)
        self._refresh_models()

    def _on_accept(self) -> None:
        try:
            self._save_settings()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.accept()

    def _save_settings(self) -> None:
        values = self.form.collect_settings()

        for key, value in values.get("app", {}).items():
            self.config_manager.set(f"app.{key}", value)

        for provider, cfg in values.get("providers", {}).items():
            for key, value in cfg.items():
                self.config_manager.set(f"providers.{provider}.{key}", value)

        for key, value in values.get("security", {}).items():
            self.config_manager.set(f"security.{key}", value)

        self.config_manager.save()
        self.saved_config = self.config_manager.get_all()

    def _refresh_models(self) -> None:
        self.form.refresh_models_btn.setEnabled(False)
        self.form.models_status_label.setText("正在刷新模型列表…")

        async def fetch():
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

