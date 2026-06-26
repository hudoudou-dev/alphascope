# AlphaScope 部署指南

## 环境要求

- Python 3.10+
- pandas >= 2.0
- numpy >= 1.24
- streamlit >= 1.28
- plotly >= 5.18

## 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/alphascope.git
cd alphascope

# 安装依赖
pip install -r requirements.txt
```

## 配置

编辑 `config/settings.yaml`：

```yaml
data:
  providers:
    akshare:
      enabled: true
    baostock:
      enabled: true
    tushare:
      enabled: true
      token: ${TUSHARE_TOKEN}  # 使用环境变量

  storage:
    base_path: "./data"

backtest:
  initial_cash: 1000000.0
  commission_rate: 0.0003
  slippage_rate: 0.001
```

## 启动

### Web 平台

```bash
streamlit run src/web/app.py
```

### 调度服务

```bash
python -m src.scheduler.scheduler_service
```

## 数据下载

首次使用需要下载交易日历：

```python
from src.calendar.trading_calendar import TradingCalendarService

calendar = TradingCalendarService()
calendar.download_trading_days("1990-12-19", "2030-12-31")
```

## 生产环境

### Systemd 服务

```ini
[Unit]
Description=AlphaScope Scheduler
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/alphascope
ExecStart=/path/to/venv/bin/python -m src.scheduler.scheduler_service
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker (可选)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "src/web/app.py"]
```

## 通知配置

### 钉钉

在 `config/settings.yaml` 中配置：

```yaml
notifier:
  dingtalk:
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
```

### 飞书

```yaml
notifier:
  feishu:
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK"
```