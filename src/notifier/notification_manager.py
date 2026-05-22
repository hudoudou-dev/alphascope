from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import config_loader
from src.core.logger import get_logger


class EventType(str, Enum):
    DATA_UPDATE = "data_update"
    BACKTEST_COMPLETE = "backtest_complete"
    STRATEGY_ERROR = "strategy_error"
    SCHEDULE_FAILURE = "schedule_failure"
    DAILY_REPORT = "daily_report"


@dataclass
class NotificationMessage:
    event_type: EventType
    message: str
    strategy_name: str | None = None
    timestamp: datetime | None = None
    extra_data: dict[str, Any] | None = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": self.event_type.value,
            "message": self.message,
            "strategy_name": self.strategy_name,
            "extra_data": self.extra_data,
        }


class BaseNotifier(ABC):
    
    def __init__(self, webhook_url: str, retry_times: int | None = None, timeout: int | None = None):
        self.webhook_url = webhook_url
        self.retry_times = retry_times or 3
        self.timeout = timeout or 10
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        pass
    
    def _format_message(self, message: NotificationMessage) -> dict[str, Any]:
        return message.to_dict()


class DingTalkNotifier(BaseNotifier):
    
    def send(self, message: NotificationMessage) -> bool:
        payload = self._build_payload(message)
        
        try:
            response = self._send_request(payload)
            
            if response.get("errcode") == 0:
                self.logger.info(
                    "DingTalk notification sent successfully",
                    event_type=message.event_type.value,
                )
                return True
            else:
                self.logger.error(
                    "DingTalk notification failed",
                    error=response.get("errmsg"),
                    event_type=message.event_type.value,
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "DingTalk notification exception",
                error=str(e),
                event_type=message.event_type.value,
            )
            return False
    
    def _build_payload(self, message: NotificationMessage) -> dict[str, Any]:
        title = self._get_title(message.event_type)
        
        content = f"**{title}**\n\n"
        content += f"📅 时间: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"📋 事件: {message.event_type.value}\n\n"
        
        if message.strategy_name:
            content += f"🎯 策略: {message.strategy_name}\n\n"
        
        content += f"💬 消息: {message.message}"
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
            },
        }
    
    def _get_title(self, event_type: EventType) -> str:
        titles = {
            EventType.DATA_UPDATE: "📊 数据更新完成",
            EventType.BACKTEST_COMPLETE: "📈 回测完成",
            EventType.STRATEGY_ERROR: "⚠️ 策略异常",
            EventType.SCHEDULE_FAILURE: "❌ 调度失败",
            EventType.DAILY_REPORT: "📊 每日报告",
        }
        return titles.get(event_type, "📢 系统通知")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _send_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


class FeishuNotifier(BaseNotifier):
    
    def send(self, message: NotificationMessage) -> bool:
        payload = self._build_payload(message)
        
        try:
            response = self._send_request(payload)
            
            if response.get("StatusCode") == 0:
                self.logger.info(
                    "Feishu notification sent successfully",
                    event_type=message.event_type.value,
                )
                return True
            else:
                self.logger.error(
                    "Feishu notification failed",
                    error=response.get("msg"),
                    event_type=message.event_type.value,
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "Feishu notification exception",
                error=str(e),
                event_type=message.event_type.value,
            )
            return False
    
    def _build_payload(self, message: NotificationMessage) -> dict[str, Any]:
        title = self._get_title(message.event_type)
        
        content = []
        content.append([{"tag": "text", "text": f"{title}\n"}])
        content.append([{"tag": "text", "text": f"📅 时间: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"}])
        content.append([{"tag": "text", "text": f"📋 事件: {message.event_type.value}"}])
        
        if message.strategy_name:
            content.append([{"tag": "text", "text": f"🎯 策略: {message.strategy_name}"}])
        
        content.append([{"tag": "text", "text": f"💬 消息: {message.message}"}])
        
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title,
                    },
                    "template": self._get_color(message.event_type),
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "\n".join([item[0]["text"] for item in content]),
                        },
                    }
                ],
            },
        }
    
    def _get_title(self, event_type: EventType) -> str:
        titles = {
            EventType.DATA_UPDATE: "📊 数据更新完成",
            EventType.BACKTEST_COMPLETE: "📈 回测完成",
            EventType.STRATEGY_ERROR: "⚠️ 策略异常",
            EventType.SCHEDULE_FAILURE: "❌ 调度失败",
            EventType.DAILY_REPORT: "📊 每日报告",
        }
        return titles.get(event_type, "📢 系统通知")
    
    def _get_color(self, event_type: EventType) -> str:
        colors = {
            EventType.DATA_UPDATE: "blue",
            EventType.BACKTEST_COMPLETE: "green",
            EventType.STRATEGY_ERROR: "red",
            EventType.SCHEDULE_FAILURE: "red",
            EventType.DAILY_REPORT: "blue",
        }
        return colors.get(event_type, "blue")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _send_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


class NotificationManager:
    
    def __init__(self):
        config = config_loader.get("notification", {})
        
        self.notifiers: list[BaseNotifier] = []
        self.logger = get_logger(self.__class__.__name__)
        
        self._init_notifiers(config)
    
    def _init_notifiers(self, config: dict[str, Any]) -> None:
        dingtalk_config = config.get("dingtalk", {})
        if dingtalk_config.get("enabled", False):
            webhook_url = dingtalk_config.get("webhook_url")
            if webhook_url:
                self.notifiers.append(
                    DingTalkNotifier(
                        webhook_url=webhook_url,
                        retry_times=dingtalk_config.get("retry_times", 3),
                        timeout=dingtalk_config.get("timeout", 10),
                    )
                )
                self.logger.info("DingTalk notifier initialized")
        
        feishu_config = config.get("feishu", {})
        if feishu_config.get("enabled", False):
            webhook_url = feishu_config.get("webhook_url")
            if webhook_url:
                self.notifiers.append(
                    FeishuNotifier(
                        webhook_url=webhook_url,
                        retry_times=feishu_config.get("retry_times", 3),
                        timeout=feishu_config.get("timeout", 10),
                    )
                )
                self.logger.info("Feishu notifier initialized")
    
    def notify(self, message: NotificationMessage) -> bool:
        if not self.notifiers:
            self.logger.warning("No notifiers configured")
            return False
        
        results = []
        for notifier in self.notifiers:
            try:
                result = notifier.send(message)
                results.append(result)
            except Exception as e:
                self.logger.error(
                    "Notifier failed",
                    notifier=notifier.__class__.__name__,
                    error=str(e),
                )
                results.append(False)
        
        success = any(results)
        
        if success:
            self.logger.info(
                "Notification sent successfully",
                event_type=message.event_type.value,
                success_count=sum(results),
                total_count=len(results),
            )
        else:
            self.logger.error(
                "All notifiers failed",
                event_type=message.event_type.value,
            )
        
        return success
    
    def notify_data_update(self, message: str, strategy_name: str | None = None) -> bool:
        notification = NotificationMessage(
            event_type=EventType.DATA_UPDATE,
            message=message,
            strategy_name=strategy_name,
        )
        return self.notify(notification)
    
    def notify_backtest_complete(
        self,
        message: str,
        strategy_name: str,
        extra_data: dict[str, Any] | None = None,
    ) -> bool:
        notification = NotificationMessage(
            event_type=EventType.BACKTEST_COMPLETE,
            message=message,
            strategy_name=strategy_name,
            extra_data=extra_data,
        )
        return self.notify(notification)
    
    def notify_strategy_error(
        self,
        message: str,
        strategy_name: str,
        extra_data: dict[str, Any] | None = None,
    ) -> bool:
        notification = NotificationMessage(
            event_type=EventType.STRATEGY_ERROR,
            message=message,
            strategy_name=strategy_name,
            extra_data=extra_data,
        )
        return self.notify(notification)
    
    def notify_schedule_failure(self, message: str, extra_data: dict[str, Any] | None = None) -> bool:
        notification = NotificationMessage(
            event_type=EventType.SCHEDULE_FAILURE,
            message=message,
            extra_data=extra_data,
        )
        return self.notify(notification)
    
    def notify_daily_report(
        self,
        message: str,
        strategy_name: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> bool:
        notification = NotificationMessage(
            event_type=EventType.DAILY_REPORT,
            message=message,
            strategy_name=strategy_name,
            extra_data=extra_data,
        )
        return self.notify(notification)