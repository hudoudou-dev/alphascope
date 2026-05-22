# Data Contract

## 1. 标准 OHLCV Schema

所有市场数据必须包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| date | datetime | 交易日期 |
| open_price | float | 开盘价 |
| high_price | float | 最高价 |
| low_price | float | 最低价 |
| close_price | float | 收盘价 |
| volume | float | 成交量 |
| amount | float | 成交额 |
| pct_chg | float | 涨跌幅 |
| turn | float | 换手率 |
| code | str | 股票代码 |
| name | str | 股票名称 |

---

## 2. 技术指标字段

| 字段 | 类型 |
|---|---|
| ma5 | float |
| ma10 | float |
| ma20 | float |
| rsi | float |
| macd | float |

---

## 3. parquet 规范

必须：

- 使用 snappy 压缩
- 使用 pyarrow
- 按股票代码分文件

---

## 4. 时间规范

所有时间必须：

- 使用 Asia/Shanghai
- 使用 datetime64[ns]
- 格式: YYYY-MM-DD


---

## 5. 数据限制

禁止：

- 空日期
- 重复日期
- 负价格
- 未来日期

## 6. 数据规范

所有股票代码必须统一为：

<6位数字>.<EXCHANGE>

示例:
600000.SH
000001.SZ
300750.SZ
688001.SH
830001.BJ

禁止:
sh600001
sz000001
600001
sh.600001
SH600001

本地数据存储格式:
600000.SH.parquet
000001.SZ.parquet
688001.SH.parquet


