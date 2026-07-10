# 配置参数说明

本文档详细说明 AlphaScope 的所有配置参数。

## 配置文件位置

```
config/settings.yaml
```

---

## 数据模块 (data)

### 数据提供者配置

#### AKShare
```yaml
data:
  providers:
    akshare:
      enabled: true
      retry_times: 3
      retry_delay: 1.0
```

#### BaoStock
```yaml
    baostock:
      enabled: true
      retry_times: 3
      retry_delay: 1.0
```

#### Tushare
```yaml
    tushare:
      enabled: true
      token: ${TUSHARE_TOKEN}
      retry_times: 3
      retry_delay: 1.0
```

### 存储配置

```yaml
  storage:
    base_path: ./data
    compression: snappy
    partition_by: code
```

### 更新配置

```yaml
  update:
    incremental: true
    lookback_days: 30
```

### 验证配置

```yaml
  validation:
    check_future_date: true
    check_negative_price: true
    check_duplicate_date: true
    check_missing_values: true
```

---

## 策略模块 (strategy)

### 子策略融合权重与超参

```yaml
strategy:
  sub_strategies:
    # 4 套子策略融合权重（总和归一化为 100%）
    trend_weight: 30.0
    momentum_weight: 25.0
    volume_price_weight: 25.0
    quality_weight: 20.0

    # 策略A：趋势跟踪
    trend:
      adx_weight: 0.30
      ma_weight: 0.30
      macd_weight: 0.20
      pullback_weight: 0.20
      adx_strong_threshold: 25.0
      adx_weak_threshold: 20.0
      # ... 全部因子阈值与评分值（见 config/settings.yaml）

    # 策略B：动量反转
    momentum:
      short_reversal_weight: 0.35
      multi_momentum_weight: 0.35
      rsi_weight: 0.30
      # ...

    # 策略C：量价共振
    volume_price:
      vol_ratio_weight: 0.30
      turnover_weight: 0.15
      vp_corr_weight: 0.20
      obv_weight: 0.20
      shrink_stop_weight: 0.15
      # ...

    # 策略D：低波动质量
    quality:
      volatility_weight: 0.30
      skewness_weight: 0.20
      downside_weight: 0.20
      fundamental_weight: 0.30
      # ...
```

### 选股筛选配置

```yaml
  selection:
    # 市值与价格
    market_cap_min: 50.0       # 最小市值（亿元）
    market_cap_max: 20000.0    # 最大市值（亿元）
    price_min: 5.0             # 最小股价
    price_max: 2000.0          # 最大股价

    # 涨跌停
    limit_up_min: 0
    limit_down_max: 3
    limit_stat_period: 20      # 统计周期（天）
    max_up_threshold: 10.0     # 涨停阈值
    max_down_threshold: -10.0  # 跌停阈值

    # 持仓
    initial_cash: 1000000.0
    max_positions: 10
    top_n: 20                  # 候选 Top-N
    min_score_threshold: 50.0  # 最低评分（唯一来源）

    # 交易频率
    cooldown_days: 5
    max_trades_per_day: 5

    # 风控
    enable_risk_control: true
    enable_st_filter: true
    enable_limit_filter: true

    # 横截面 / 行情自适应开关（默认关闭）
    cross_sectional_enabled: false
    regime_enabled: false
```

### 缺失数据处理

```yaml
  missing_data:
    mode: redistribute   # redistribute | neutral | penalize | exclude
```

### 横截面标准化（默认关闭）

```yaml
  cross_sectional:
    enabled: false
    method: zscore       # zscore | rank
```

### 行情自适应（默认关闭）

```yaml
  regime:
    enabled: false
    breadth_bull: 0.60   # 多头广度阈值（牛）
    breadth_trend: 0.50  # 多头广度阈值（趋势）
    breadth_bear: 0.40   # 多头广度阈值（熊）
    vol_high: 0.50       # 高波动阈值
    vol_low: 0.30        # 低波动阈值
```

---

## 技术指标模块 (indicators)

```yaml
indicators:
  ma:
    periods: [5, 10, 20, 60]
  rsi:
    period: 14
    oversold: 30
    overbought: 70
  macd:
    fast_period: 12
    slow_period: 26
    signal_period: 9
  bollinger_bands:
    period: 20
    std_dev: 2.0
```

---

## 回测模块 (backtest)

```yaml
backtest:
  initial_cash: 1000000.0
  commission_rate: 0.0003     # 万三
  stamp_duty_rate: 0.001      # 千一
  min_commission: 5.0
  trading_days_per_year: 252
```

---

## 通知模块 (notification)

```yaml
notification:
  dingtalk:
    enabled: false
    webhook_url: ""
    retry_times: 3
  feishu:
    enabled: false
    webhook_url: ""
    retry_times: 3
```

---

## 日志配置 (logging)

```yaml
logging:
  level: INFO
  format: json
  timezone: Asia/Shanghai
```

---

## 全局配置

```yaml
timezone: Asia/Shanghai
```

---

## 配置优先级

1. **代码中显式传入的参数** - 最高优先级
2. **配置文件中的参数** - 中等优先级
3. **代码中的默认值** - 最低优先级

---

## 环境变量

```yaml
data:
  providers:
    tushare:
      token: ${TUSHARE_TOKEN}
```

```bash
export TUSHARE_TOKEN="your_token_here"
```

---

## 配置最佳实践

1. 不要提交敏感信息（Webhook URL、Token 使用环境变量）
2. 根据环境调整（开发/生产使用不同配置）
3. 定期备份配置文件
4. 新增配置项保持向后兼容（默认关闭或不影响既有行为）
