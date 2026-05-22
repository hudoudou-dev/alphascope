# Notification Contract

## 支持 Provider

- Feishu
- DingTalk

---

## 通知事件

- 数据更新完成
- 回测完成
- 策略异常
- 调度失败

---

## 通知格式

必须包含：

- timestamp
- event_type
- message
- strategy_name

---

## Retry

通知失败必须 retry。