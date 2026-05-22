from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.notifier.notification_manager import (
    DingTalkNotifier,
    EventType,
    FeishuNotifier,
    NotificationManager,
    NotificationMessage,
)


@pytest.fixture
def sample_message() -> NotificationMessage:
    return NotificationMessage(
        event_type=EventType.DATA_UPDATE,
        message="数据更新完成",
        strategy_name="TestStrategy",
    )


@pytest.fixture
def mock_dingtalk_response():
    return {"errcode": 0, "errmsg": "ok"}


@pytest.fixture
def mock_feishu_response():
    return {"StatusCode": 0, "msg": "success"}


class TestNotificationMessage:
    
    def test_init(self):
        message = NotificationMessage(
            event_type=EventType.DATA_UPDATE,
            message="Test message",
        )
        
        assert message.event_type == EventType.DATA_UPDATE
        assert message.message == "Test message"
        assert message.timestamp is not None
    
    def test_to_dict(self, sample_message: NotificationMessage):
        result = sample_message.to_dict()
        
        assert "timestamp" in result
        assert "event_type" in result
        assert "message" in result
        assert result["event_type"] == "data_update"


class TestDingTalkNotifier:
    
    def test_init(self):
        notifier = DingTalkNotifier(webhook_url="https://oapi.dingtalk.com/robot/send?access_token=test")
        
        assert notifier.webhook_url == "https://oapi.dingtalk.com/robot/send?access_token=test"
        assert notifier.retry_times == 3
    
    @patch("requests.post")
    def test_send_success(self, mock_post, sample_message: NotificationMessage, mock_dingtalk_response):
        mock_response = MagicMock()
        mock_response.json.return_value = mock_dingtalk_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        notifier = DingTalkNotifier(webhook_url="https://oapi.dingtalk.com/robot/send?access_token=test")
        result = notifier.send(sample_message)
        
        assert result is True
        mock_post.assert_called_once()
    
    @patch("requests.post")
    def test_send_failure(self, mock_post, sample_message: NotificationMessage):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 1, "errmsg": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        notifier = DingTalkNotifier(webhook_url="https://oapi.dingtalk.com/robot/send?access_token=test")
        result = notifier.send(sample_message)
        
        assert result is False
    
    def test_build_payload(self, sample_message: NotificationMessage):
        notifier = DingTalkNotifier(webhook_url="https://oapi.dingtalk.com/robot/send?access_token=test")
        payload = notifier._build_payload(sample_message)
        
        assert "msgtype" in payload
        assert payload["msgtype"] == "markdown"
        assert "markdown" in payload


class TestFeishuNotifier:
    
    def test_init(self):
        notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test")
        
        assert notifier.webhook_url == "https://open.feishu.cn/open-apis/bot/v2/hook/test"
        assert notifier.retry_times == 3
    
    @patch("requests.post")
    def test_send_success(self, mock_post, sample_message: NotificationMessage, mock_feishu_response):
        mock_response = MagicMock()
        mock_response.json.return_value = mock_feishu_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test")
        result = notifier.send(sample_message)
        
        assert result is True
        mock_post.assert_called_once()
    
    @patch("requests.post")
    def test_send_failure(self, mock_post, sample_message: NotificationMessage):
        mock_response = MagicMock()
        mock_response.json.return_value = {"StatusCode": 1, "msg": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test")
        result = notifier.send(sample_message)
        
        assert result is False
    
    def test_build_payload(self, sample_message: NotificationMessage):
        notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test")
        payload = notifier._build_payload(sample_message)
        
        assert "msg_type" in payload
        assert payload["msg_type"] == "interactive"
        assert "card" in payload


class TestNotificationManager:
    
    def test_init_no_config(self):
        with patch("src.notifier.notification_manager.config_loader") as mock_loader:
            mock_loader.get.return_value = {}
            manager = NotificationManager()
            
            assert len(manager.notifiers) == 0
    
    @patch("src.notifier.notification_manager.DingTalkNotifier")
    def test_init_with_dingtalk(self, mock_dingtalk):
        with patch("src.notifier.notification_manager.config_loader") as mock_loader:
            mock_loader.get.return_value = {
                "dingtalk": {
                    "enabled": True,
                    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test",
                }
            }
            
            manager = NotificationManager()
            
            assert len(manager.notifiers) == 1
    
    @patch("src.notifier.notification_manager.FeishuNotifier")
    def test_init_with_feishu(self, mock_feishu):
        with patch("src.notifier.notification_manager.config_loader") as mock_loader:
            mock_loader.get.return_value = {
                "feishu": {
                    "enabled": True,
                    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test",
                }
            }
            
            manager = NotificationManager()
            
            assert len(manager.notifiers) == 1
    
    def test_notify_no_notifiers(self):
        with patch("src.notifier.notification_manager.config_loader") as mock_loader:
            mock_loader.get.return_value = {}
            manager = NotificationManager()
            
            message = NotificationMessage(
                event_type=EventType.DATA_UPDATE,
                message="Test",
            )
            
            result = manager.notify(message)
            
            assert result is False
    
    def test_notify_data_update(self):
        with patch("src.notifier.notification_manager.config_loader") as mock_loader:
            mock_loader.get.return_value = {}
            manager = NotificationManager()
            
            with patch.object(manager, "notify") as mock_notify:
                mock_notify.return_value = True
                
                result = manager.notify_data_update("数据更新完成", "TestStrategy")
                
                mock_notify.assert_called_once()
                assert result is True
    
    def test_notify_backtest_complete(self):
        with patch("src.notifier.notification_manager.config_loader") as mock_loader:
            mock_loader.get.return_value = {}
            manager = NotificationManager()
            
            with patch.object(manager, "notify") as mock_notify:
                mock_notify.return_value = True
                
                result = manager.notify_backtest_complete("回测完成", "TestStrategy")
                
                mock_notify.assert_called_once()
                assert result is True
    
    def test_notify_strategy_error(self):
        with patch("src.notifier.notification_manager.config_loader") as mock_loader:
            mock_loader.get.return_value = {}
            manager = NotificationManager()
            
            with patch.object(manager, "notify") as mock_notify:
                mock_notify.return_value = True
                
                result = manager.notify_strategy_error("策略异常", "TestStrategy")
                
                mock_notify.assert_called_once()
                assert result is True


class TestEventType:
    
    def test_event_types(self):
        assert EventType.DATA_UPDATE == "data_update"
        assert EventType.BACKTEST_COMPLETE == "backtest_complete"
        assert EventType.STRATEGY_ERROR == "strategy_error"
        assert EventType.SCHEDULE_FAILURE == "schedule_failure"
        assert EventType.DAILY_REPORT == "daily_report"