# 通知系统使用指南

本文档展示如何使用 AlphaScope 的通知系统模块。

## 安装依赖

```bash
pip install requests tenacity
```

## 配置

在 `config/settings.yaml` 中配置通知系统：

```yaml
notification:
  dingtalk:
    enabled: true
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
    retry_times: 3
  
  feishu:
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_TOKEN"
    retry_times: 3
```

## 基本使用

### 1. 初始化通知管理器

```python
from src.notifier.notification_manager import NotificationManager

# 初始化
manager = NotificationManager()
```

### 2. 发送通知

```python
# 数据更新通知
manager.notify_data_update(
    message="数据更新完成，共下载 100 只股票数据",
    strategy_name="SimpleMAStrategy",
)

# 回测完成通知
manager.notify_backtest_complete(
    message="回测完成，总收益率 15.2%",
    strategy_name="SimpleMAStrategy",
    extra_data={
        "total_return": 15.2,
        "sharpe_ratio": 1.5,
    },
)

# 策略异常通知
manager.notify_strategy_error(
    message="策略执行失败：数据缺失",
    strategy_name="SimpleMAStrategy",
)

# 调度失败通知
manager.notify_schedule_failure(
    message="定时任务执行失败",
)

# 每日报告通知
manager.notify_daily_report(
    message="今日选股结果：推荐买入 600000.SH",
    strategy_name="SimpleMAStrategy",
)
```

## 支持的通知渠道

### 钉钉（DingTalk）

1. 在钉钉群中添加自定义机器人
2. 获取 Webhook URL
3. 配置到 `config/settings.yaml`

**消息格式：**
- Markdown 格式
- 包含标题、时间、事件类型、策略名称、消息内容

### 飞书（Feishu）

1. 在飞书群中添加自定义机器人
2. 获取 Webhook URL
3. 配置到 `config/settings.yaml`

**消息格式：**
- 卡片消息
- 包含标题、时间、事件类型、策略名称、消息内容
- 根据事件类型显示不同颜色

## 事件类型

| 事件类型 | 说明 | 图标 |
|---------|------|------|
| DATA_UPDATE | 数据更新完成 | 📊 |
| BACKTEST_COMPLETE | 回测完成 | 📈 |
| STRATEGY_ERROR | 策略异常 | ⚠️ |
| SCHEDULE_FAILURE | 调度失败 | ❌ |
| DAILY_REPORT | 每日报告 | 📊 |

## 完整示例

```python
from src.notifier.notification_manager import NotificationManager

# 初始化
manager = NotificationManager()

# 发送数据更新通知
manager.notify_data_update(
    message="成功下载 5000 只股票数据",
    strategy_name="DataDownloader",
)

# 发送回测完成通知
manager.notify_backtest_complete(
    message="回测完成，总收益率 25.8%，夏普比率 2.1",
    strategy_name="TrendFollowing",
    extra_data={
        "total_return": 25.8,
        "annual_return": 45.2,
        "max_drawdown": 8.5,
        "sharpe_ratio": 2.1,
    },
)

# 发送策略异常通知
manager.notify_strategy_error(
    message="策略执行失败：股票数据缺失",
    strategy_name="MACDStrategy",
    extra_data={
        "error_code": "DATA_MISSING",
        "stock_code": "600000.SH",
    },
)
```

## 重试机制

通知系统内置重试机制：

- 默认重试 3 次
- 指数退避（1s, 2s, 4s）
- 失败后记录日志

## 注意事项

1. **Webhook URL 安全**: 不要将 Webhook URL 提交到代码仓库
2. **通知频率**: 避免频繁发送通知
3. **错误处理**: 通知失败不会影响主流程
4. **日志记录**: 所有通知都会记录日志

## 故障排除

### 问题 1: 通知未发送

```bash
# 检查配置
cat config/settings.yaml

# 检查日志
tail -f logs/alphascope.log | grep "notification"
```

### 问题 2: 钉钉通知失败

```bash
# 测试 Webhook
curl -X POST \
  'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"msgtype":"text","text":{"content":"测试消息"}}'
```

### 问题 3: 飞书通知失败

```bash
# 测试 Webhook
curl -X POST \
  'https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"msg_type":"text","content":{"text":"测试消息"}}'
```