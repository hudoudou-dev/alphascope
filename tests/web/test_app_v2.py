"""
Web应用V2单元测试
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.app_v2 import DownloadManager, DownloadProgress, DownloadTask


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
    
    def test_with_adjust(self):
        task = DownloadTask(
            code="600000.SH",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            adjust="qfq",
        )
        
        assert task.adjust == "qfq"


class TestDownloadProgress:
    
    def test_init(self):
        progress = DownloadProgress()
        
        assert progress.total == 0
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.current_code == ""
    
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


class TestDownloadManager:
    
    def test_init(self):
        manager = DownloadManager()
        
        assert manager.is_running is False
        assert isinstance(manager.progress, DownloadProgress)
    
    @patch("src.web.app_v2.AKShareProvider")
    def test_get_provider_akshare(self, mock_provider):
        manager = DownloadManager()
        provider = manager._get_provider("akshare")
        
        assert provider is not None
    
    @patch("src.web.app_v2.BaoStockProvider")
    def test_get_provider_baostock(self, mock_provider):
        manager = DownloadManager()
        provider = manager._get_provider("baostock")
        
        assert provider is not None
    
    @patch("src.web.app_v2.TushareProvider")
    def test_get_provider_tushare(self, mock_provider):
        manager = DownloadManager()
        provider = manager._get_provider("tushare")
        
        assert provider is not None
    
    def test_stop_download(self):
        manager = DownloadManager()
        manager.is_running = True
        
        manager.stop_download()
        
        assert manager.is_running is False