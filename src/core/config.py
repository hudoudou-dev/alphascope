from pathlib import Path
from typing import Any
import os
import re

import yaml


class EnvVarLoader(yaml.SafeLoader):
    pass


def env_var_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    value = loader.construct_scalar(node)
    pattern = r'\$\{([^}]+)\}'
    matches = re.findall(pattern, value)
    for match in matches:
        env_value = os.environ.get(match, '')
        value = value.replace(f'${{{match}}}', env_value)
    return value


EnvVarLoader.add_constructor('!env', env_var_constructor)


class ConfigLoader:
    
    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"
        self.config_path = Path(config_path)
        self._config: dict[str, Any] | None = None
    
    def _expand_env_vars(self, content: str) -> str:
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, content)
        for match in matches:
            env_value = os.environ.get(match, '')
            content = content.replace(f'${{{match}}}', env_value)
        return content
    
    def load(self) -> dict[str, Any]:
        if self._config is None:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = self._expand_env_vars(content)
                self._config = yaml.safe_load(content)
            else:
                self._config = self._get_default_config()
        return self._config
    
    def save(self, config: dict[str, Any]) -> None:
        """保存配置到文件"""
        # 确保配置目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存配置到文件
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # 更新缓存的配置
        self._config = config
    
    def update(self, key: str, value: Any) -> None:
        """更新配置中的某个键值"""
        config = self.load()
        keys = key.split(".")
        
        # 逐层访问并更新
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 更新最后一个键的值
        current[keys[-1]] = value
        
        # 保存配置
        self.save(config)
    
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
