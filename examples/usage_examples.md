# Data Provider 使用示例

本文档展示如何使用 AlphaScope 的数据提供者模块。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 基本使用

### 1. 使用 AKShare Provider

```python
from datetime import datetime
from src.data.providers.akshare_provider import AKShareProvider

# 初始化
provider = AKShareProvider(storage_path="./data")

# 下载日线数据
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 31)
df = provider.download_and_save("600000.SH", start_date, end_date, adjust="qfq")

print(f"下载了 {len(df)} 条数据")
print(df.head())

# 增量更新
updated_df = provider.incremental_update("600000.SH", datetime.now())

# 获取股票列表
stock_list = provider.get_stock_list()
print(f"共 {len(stock_list)} 只股票")
```

### 2. 使用 BaoStock Provider

```python
from src.data.providers.baostock_provider import BaoStockProvider

# 使用上下文管理器自动登录/登出
with BaoStockProvider(storage_path="./data") as provider:
    # 下载数据
    df = provider.download_and_save("000001.SZ", start_date, end_date)
    
    # 获取交易日历
    trade_dates = provider.get_trade_calendar(start_date, end_date)
    print(f"交易日: {trade_dates}")
```

### 3. 使用 Tushare Provider

```python
import os
from src.data.providers.tushare_provider import TushareProvider

# 设置 token
os.environ["TUSHARE_TOKEN"] = "your_token_here"

# 初始化
provider = TushareProvider(storage_path="./data")

# 下载数据
df = provider.download_and_save("600000.SH", start_date, end_date, adjust="qfq")

# 获取每日基本面数据
basic_info = provider.get_daily_basic("600000.SH", datetime(2024, 1, 1))
print(basic_info)
```

## 数据验证

所有数据提供者都会自动进行数据验证：

```python
from src.data.schema import DataValidator
import pandas as pd

# 创建验证器
validator = DataValidator(
    check_future_date=True,
    check_negative_price=True,
    check_duplicate_date=True,
    check_missing_values=True,
)

# 验证数据
df = pd.DataFrame({
    "date": [datetime(2024, 1, 1)],
    "open_price": [10.0],
    "high_price": [10.5],
    "low_price": [9.5],
    "close_price": [10.2],
    "volume": [1000000.0],
    "amount": [10000000.0],
    "code": ["600000.SH"],
})

# 验证
validated_df = validator.validate(df)

# 类型转换
typed_df = validator.cast_dtypes(df)
```

## Parquet 存储

数据自动以 Parquet 格式存储：

```python
import pyarrow.parquet as pq

# 读取 parquet 文件
table = pq.read_table("./data/600000.SH.parquet")
df = table.to_pandas()

print(df.head())
```

## 配置管理

通过 YAML 配置文件管理所有参数：

```yaml
# config/settings.yaml
data:
  providers:
    akshare:
      enabled: true
      retry_times: 3
      retry_delay: 1.0
  
  storage:
    base_path: ./data
    compression: snappy
    
  validation:
    check_future_date: true
    check_negative_price: true
```

## 错误处理

所有提供者都支持自动重试：

```python
from tenacity import retry, stop_after_attempt, wait_exponential

# 自动重试 3 次，指数退避
df = provider.download_and_save("600000.SH", start_date, end_date)
```

## 日志记录

所有操作都有结构化日志：

```python
from src.core.logger import get_logger

logger = get_logger("my_module")
logger.info("开始下载数据", code="600000.SH", start_date=str(start_date))
```

## 完整示例

```python
from datetime import datetime
from src.data.providers.akshare_provider import AKShareProvider

def download_stock_data():
    # 初始化
    provider = AKShareProvider(storage_path="./data")
    
    # 获取股票列表
    stock_list = provider.get_stock_list()
    
    # 下载前 10 只股票的数据
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    for code in stock_list[:10]:
        try:
            df = provider.download_and_save(code, start_date, end_date)
            print(f"{code}: {len(df)} 条数据")
        except Exception as e:
            print(f"{code}: 下载失败 - {e}")

if __name__ == "__main__":
    download_stock_data()
```

## 注意事项

1. **未来数据检查**: 系统会自动拒绝未来日期的数据
2. **价格验证**: 所有价格必须为正数，且 high >= low
3. **重复数据**: 系统会自动去重
4. **时区**: 所有时间使用 Asia/Shanghai 时区
5. **股票代码格式**: 统一使用 `XXXXXX.EXCHANGE` 格式（如 600000.SH）
