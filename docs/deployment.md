# AlphaScope 部署指南

## 环境要求

- Python 3.12+
- Node.js 18+
- pandas >= 2.0
- numpy >= 1.24

## 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/alphascope.git
cd alphascope

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd web && npm install
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
      token: ${TUSHARE_TOKEN}

  storage:
    base_path: "./data"

backtest:
  initial_cash: 1000000.0
  commission_rate: 0.0003

strategy:
  sub_strategies:
    trend_weight: 30.0
    momentum_weight: 25.0
    volume_price_weight: 25.0
    quality_weight: 20.0
  # ... 更多超参见配置指南
```

## 启动

### 后端 (FastAPI)

```bash
# 开发模式
python -m src.api.main

# 或使用 uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档：http://localhost:8000/docs

### 前端 (Vue.js)

```bash
cd web
npm run dev
```

访问 http://localhost:5173

### 数据下载

首次使用需要下载交易日历和股票数据：

```python
from src.calendar.trading_calendar import TradingCalendarService

calendar = TradingCalendarService()
calendar.download_trading_days("1990-12-19", "2030-12-31")
```

然后在 Web 前端「股票数据更新」页面进行数据下载。

## 生产环境

### 后端

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 前端

```bash
cd web && npm run build
# 将 dist/ 部署到 Nginx 等静态服务器
```

### Systemd 服务

```ini
[Unit]
Description=AlphaScope API
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/alphascope
ExecStart=/path/to/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker

```dockerfile
# 后端
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 通知配置

### 钉钉

```yaml
notification:
  dingtalk:
    enabled: true
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
```

### 飞书

```yaml
notification:
  feishu:
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK"
```
