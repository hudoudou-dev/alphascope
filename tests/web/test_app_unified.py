"""
统一Web应用单元测试
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.app_unified import (
    AutoSwitchProvider,
    DownloadManager,
    DownloadProgress,
    DownloadTask,
)


class TestDownloadTask:
    
    def test_init(self):
        task = DownloadTask(
            code="600000.SH",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )
        
        assert task.code == "600000.SH"
        assert task.status == "pending"
        assert task.error is None
        assert task.rows == 0
        assert task.provider == ""
    
    def test_with_provider(self):
        task = DownloadTask(
            code="600000.SH",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            provider="akshare",
        )
        
        assert task.provider == "akshare"


class TestDownloadProgress:
    
    def test_init(self):
        progress = DownloadProgress()
        
        assert progress.total == 0
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.current_code == ""
        assert progress.current_provider == ""
    
    def test_progress_pct(self):
        progress = DownloadProgress(total=10, completed=5)
        
        assert progress.progress_pct == 50.0
    
    def test_progress_pct_zero_total(self):
        progress = DownloadProgress()
        
        assert progress.progress_pct == 0.0
    
    def test_eta(self):
        progress = DownloadProgress(
            total=10,
            completed=5,
            start_time=datetime.now(),
        )
        
        eta = progress.eta
        assert isinstance(eta, str)
    
    def test_eta_no_start_time(self):
        progress = DownloadProgress()
        
        assert progress.eta == "计算中..."


class TestAutoSwitchProvider:
    
    def test_init(self):
        provider_manager = AutoSwitchProvider()
        
        assert provider_manager.current_provider_index == 0
        assert len(provider_manager.provider_order) == 3
    
    @patch("src.web.app_unified.AKShareProvider")
    def test_get_provider_default(self, mock_provider):
        provider_manager = AutoSwitchProvider()
        provider = provider_manager.get_provider()
        
        assert provider is not None
    
    @patch("src.web.app_unified.BaoStockProvider")
    def test_get_provider_specific(self, mock_provider):
        provider_manager = AutoSwitchProvider()
        provider = provider_manager.get_provider("baostock")
        
        assert provider is not None
    
    def test_switch_provider(self):
        provider_manager = AutoSwitchProvider()
        
        next_provider = provider_manager.switch_provider()
        
        assert next_provider == "baostock"
        assert provider_manager.current_provider_index == 1
    
    def test_switch_provider_last(self):
        provider_manager = AutoSwitchProvider()
        provider_manager.current_provider_index = 2
        
        next_provider = provider_manager.switch_provider()
        
        assert next_provider is None
    
    def test_reset(self):
        provider_manager = AutoSwitchProvider()
        provider_manager.current_provider_index = 2
        
        provider_manager.reset()
        
        assert provider_manager.current_provider_index == 0


class TestDownloadManager:
    
    def test_init(self):
        manager = DownloadManager()
        
        assert manager.is_running is False
        assert isinstance(manager.progress, DownloadProgress)
        assert isinstance(manager.provider_manager, AutoSwitchProvider)
    
    def test_stop_download(self):
        manager = DownloadManager()
        manager.is_running = True
        
        manager.stop_download()
        
        assert manager.is_running is False