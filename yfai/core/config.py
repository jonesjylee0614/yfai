"""配置管理模块"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from yfai.providers.defaults import DEFAULT_PROVIDER_MODELS


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_env()
        self._load_config()

    def _load_env(self) -> None:
        """加载环境变量"""
        env_file = Path("configs/.env")
        if env_file.exists():
            load_dotenv(env_file)

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            # 尝试加载示例配置
            example_path = Path("configs/config.example.yaml")
            if example_path.exists():
                print(f"配置文件不存在,使用示例配置: {example_path}")
                self.config_path = example_path
            else:
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self._ensure_provider_defaults()

    def _ensure_provider_defaults(self) -> None:
        """Populate provider sections with sample model data if missing."""
        providers_cfg = self.config.setdefault("providers", {})

        for name, defaults in DEFAULT_PROVIDER_MODELS.items():
            provider_cfg = providers_cfg.setdefault(name, {})

            provider_cfg.setdefault("api_base", defaults["api_base"])
            provider_cfg.setdefault("timeout", defaults["timeout"])
            provider_cfg.setdefault("max_retries", defaults["max_retries"])
            provider_cfg.setdefault("default_model", defaults["default_model"])

            if not provider_cfg.get("models"):
                provider_cfg["models"] = defaults["models"]

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键(支持点号分隔的嵌套键)
            default: 默认值

        Returns:
            Any: 配置值
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值

        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: Optional[str] = None) -> None:
        """保存配置

        Args:
            path: 保存路径
        """
        save_path = Path(path) if path else self.config_path

        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置

        Returns:
            Dict[str, Any]: 配置字典
        """
        return self.config.copy()

