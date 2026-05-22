from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    
    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"
        self.config_path = Path(config_path)
        self._config: dict[str, Any] | None = None
    
    def load(self) -> dict[str, Any]:
        if self._config is None:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f)
            else:
                self._config = self._get_default_config()
        return self._config
    
    def _get_default_config(self) -> dict[str, Any]:
        return {
            "data": {
                "providers": {
                    "akshare": {"enabled": True, "retry_times": 3, "retry_delay": 1.0},
                    "baostock": {"enabled": True, "retry_times": 3, "retry_delay": 1.0},
                    "tushare": {"enabled": True, "token": None, "retry_times": 3, "retry_delay": 1.0},
                },
                "storage": {"base_path": "./data", "compression": "snappy", "partition_by": "code"},
                "update": {"incremental": True, "lookback_days": 30},
                "validation": {
                    "check_future_date": True,
                    "check_negative_price": True,
                    "check_duplicate_date": True,
                    "check_missing_values": True,
                },
            },
            "logging": {"level": "INFO", "format": "json", "timezone": "Asia/Shanghai"},
            "timezone": "Asia/Shanghai",
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        config = self.load()
        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    @property
    def data_config(self) -> dict[str, Any]:
        return self.get("data", {})
    
    @property
    def logging_config(self) -> dict[str, Any]:
        return self.get("logging", {})
    
    @property
    def timezone(self) -> str:
        return self.get("timezone", "Asia/Shanghai")


config_loader = ConfigLoader()
