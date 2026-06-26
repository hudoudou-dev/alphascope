from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml

from src.core.logger import get_logger
from src.strategy.base_strategy import BaseStrategy


class StrategyPlugin(ABC):
    
    @abstractmethod
    def get_strategy(self, config: dict[str, Any] | None = None) -> BaseStrategy:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass


class SimpleMAPlugin(StrategyPlugin):
    
    @property
    def name(self) -> str:
        return "SimpleMAStrategy"
    
    @property
    def description(self) -> str:
        return "Simple Moving Average crossover strategy"
    
    def get_strategy(self, config: dict[str, Any] | None = None) -> BaseStrategy:
        from src.web.app import SimpleMAStrategy
        
        ma_short = (config or {}).get("ma_short", 5)
        ma_long = (config or {}).get("ma_long", 20)
        return SimpleMAStrategy(ma_short=ma_short, ma_long=ma_long)


class StrategyPluginRegistry:
    
    def __init__(self):
        self._plugins: dict[str, StrategyPlugin] = {}
        self.logger = get_logger(self.__class__.__name__)
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self) -> None:
        self.register("SimpleMAStrategy", SimpleMAPlugin())
    
    def register(self, name: str, plugin: StrategyPlugin) -> None:
        self._plugins[name] = plugin
        self.logger.info(f"Registered strategy plugin: {name}")
    
    def unregister(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            self.logger.info(f"Unregistered strategy plugin: {name}")
            return True
        return False
    
    def get(self, name: str) -> StrategyPlugin | None:
        return self._plugins.get(name)
    
    def list_plugins(self) -> list[dict[str, str]]:
        return [
            {"name": name, "description": plugin.description}
            for name, plugin in self._plugins.items()
        ]
    
    def create_strategy(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> BaseStrategy | None:
        plugin = self.get(name)
        if plugin is None:
            self.logger.warning(f"Strategy plugin not found: {name}")
            return None
        return plugin.get_strategy(config)
    
    def load_from_directory(self, directory: str | Path) -> int:
        directory = Path(directory)
        if not directory.exists():
            return 0
        
        count = 0
        for file in directory.glob("*.yaml"):
            try:
                with open(file, "r") as f:
                    plugin_config = yaml.safe_load(f)
                
                if plugin_config and "strategy" in plugin_config:
                    strategy_config = plugin_config["strategy"]
                    name = strategy_config.get("name")
                    if name:
                        self.logger.info(f"Loading plugin from {file}: {name}")
                        count += 1
            except Exception as e:
                self.logger.warning(f"Failed to load plugin from {file}: {e}")
        
        return count
    
    def load_from_config(self, config_path: str | Path) -> int:
        config_path = Path(config_path)
        if not config_path.exists():
            return 0
        
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            if not config or "strategies" not in config:
                return 0
            
            count = 0
            for strategy_config in config["strategies"]:
                name = strategy_config.get("name")
                description = strategy_config.get("description", "")
                
                if name:
                    self.logger.info(f"Loaded strategy from config: {name}")
                    count += 1
            
            return count
        except Exception as e:
            self.logger.error(f"Failed to load strategies from config: {e}")
            return 0


_registry = StrategyPluginRegistry()


def get_registry() -> StrategyPluginRegistry:
    return _registry


def register_plugin(name: str, plugin: StrategyPlugin) -> None:
    _registry.register(name, plugin)


def create_strategy(name: str, config: dict[str, Any] | None = None) -> BaseStrategy | None:
    return _registry.create_strategy(name, config)


def list_strategies() -> list[dict[str, str]]:
    return _registry.list_plugins()