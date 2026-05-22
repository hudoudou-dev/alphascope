from datetime import datetime

from src.notifier.notification_manager import (
    EventType,
    NotificationManager,
    NotificationMessage,
)


def create_example_notifications():
    print("\n" + "="*60)
    print("通知系统使用示例")
    print("="*60)
    
    with patch("src.notifier.notification_manager.config_loader") as mock_loader:
        mock_loader.get.return_value = {}
        manager = NotificationManager()
    
    print("\n1. 数据更新通知")
    message = NotificationMessage(
        event_type=EventType.DATA_UPDATE,
        message="成功下载 5000 只股票数据",
        strategy_name="DataDownloader",
    )
    print(f"   事件类型: {message.event_type.value}")
    print(f"   消息: {message.message}")
    print(f"   策略: {message.strategy_name}")
    
    print("\n2. 回测完成通知")
    message = NotificationMessage(
        event_type=EventType.BACKTEST_COMPLETE,
        message="回测完成，总收益率 25.8%",
        strategy_name="TrendFollowing",
        extra_data={
            "total_return": 25.8,
            "sharpe_ratio": 2.1,
        },
    )
    print(f"   事件类型: {message.event_type.value}")
    print(f"   消息: {message.message}")
    print(f"   策略: {message.strategy_name}")
    print(f"   额外数据: {message.extra_data}")
    
    print("\n3. 策略异常通知")
    message = NotificationMessage(
        event_type=EventType.STRATEGY_ERROR,
        message="策略执行失败：数据缺失",
        strategy_name="MACDStrategy",
    )
    print(f"   事件类型: {message.event_type.value}")
    print(f"   消息: {message.message}")
    print(f"   策略: {message.strategy_name}")
    
    print("\n" + "-"*60)


if __name__ == "__main__":
    from unittest.mock import patch
    create_example_notifications()