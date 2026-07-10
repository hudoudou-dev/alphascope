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

### 扩展字段（通过 daily_basic 合并）

| 字段 | 类型 | 说明 |
|---|---|---|
| total_mv | float | 总市值（万元） |
| pe_ttm | float | 市盈率 TTM |
| pb | float | 市净率 |

---

## 2. 技术指标字段

| 字段 | 类型 | 说明 |
|---|---|---|
| ma5 / ma10 / ma20 / ma60 | float | 移动平均线 |
| rsi | float | 相对强弱指标 |
| macd / macd_signal / macd_hist | float | MACD 系列 |
| bb_upper / bb_middle / bb_lower | float | 布林带 |
| volume_ratio | float | 量比 |
| vp_corr | float | 量价相关性 |
| obv / obv_ma5 | float | 能量潮 |
| adx / pdi / mdi | float | 平均趋向指数 |
| atr | float | 真实波幅 |
| hist_vol | float | 年化历史波动率 |
| ret_skew | float | 收益偏度 |
| down_vol | float | 下行波动率 |

---

## 3. parquet 规范

必须：

- 使用 snappy 压缩
- 使用 pyarrow
- 按股票代码分文件
- 原始数据存入 `./data/raw/`

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

---

## 6. 股票代码规范

所有股票代码必须统一为：

```
<6位数字>.<EXCHANGE>
```

示例：
- 600000.SH
- 000001.SZ
- 300750.SZ
- 688001.SH
- 830001.BJ

禁止：
- sh600001
- sz000001
- 600001
- sh.600001
- SH600001

本地数据存储命名：
```
{code}.{name}.parquet  # 如: 300750.SZ.宁德时代.parquet
```

---

## 7. 基本面数据合并

`TushareProvider` 提供 `get_daily_basic_history()` 获取 PE/PB/市值数据，
在 `fetch_daily_data()` 主流程中通过 `_merge_daily_basic()` 合并到 OHLCV 数据帧。
缺失时优雅跳过，不影响正常数据流。
