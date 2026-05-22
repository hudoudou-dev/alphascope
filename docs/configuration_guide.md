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
      enabled: true              # 是否启用
      retry_times: 3             # 重试次数
      retry_delay: 1.0           # 重试延迟（秒）
```

#### BaoStock
```yaml
    baostock:
      enabled: true              # 是否启用
      retry_times: 3             # 重试次数
      retry_delay: 1.0           # 重试延迟（秒）
```

#### Tushare
```yaml
    tushare:
      enabled: true              # 是否启用
      token: ${TUSHARE_TOKEN}    # Tushare Token（环境变量）
      retry_times: 3             # 重试次数
      retry_delay: 1.0           # 重试延迟（秒）
```

### 存储配置

```yaml
  storage:
    base_path: ./data            # 数据存储路径
    compression: snappy          # 压缩算法
    partition_by: code           # 分区方式
```

### 更新配置

```yaml
  update:
    incremental: true            # 是否增量更新
    lookback_days: 30            # 回溯天数
```

### 验证配置

```yaml
  validation:
    check_future_date: true      # 检查未来日期
    check_negative_price: true   # 检查负价格
    check_duplicate_date: true   # 检查重复日期
    check_missing_values: true   # 检查缺失值
```

---

## 策略模块 (strategy)

### 默认策略参数

```yaml
strategy:
  default:
    stop_loss_pct: -8.0          # 止损百分比（负数）
    take_profit_pct: 20.0        # 止盈百分比
    max_position_pct: 30.0       # 单只股票最大仓位百分比
    max_positions: 10            # 最大持仓数量
    min_score_threshold: 60.0    # 最低评分阈值
```

### MA 策略参数

```yaml
  ma_strategy:
    ma_short: 5                  # 短期均线周期
    ma_long: 20                  # 长期均线周期
    score_trend_up: 75.0         # 上升趋势评分
    score_trend_up_weak: 60.0    # 弱上升趋势评分
    score_trend_down: 25.0       # 下降趋势评分
    score_neutral: 50.0          # 中性评分
```

---

## 技术指标模块 (indicators)

### MA 指标

```yaml
indicators:
  ma:
    periods: [5, 10, 20, 60]     # MA 周期列表
```

### RSI 指标

```yaml
  rsi:
    period: 14                   # RSI 周期
    oversold: 30                 # 超卖阈值
    overbought: 70               # 超买阈值
```

### MACD 指标

```yaml
  macd:
    fast_period: 12              # 快线周期
    slow_period: 26              # 慢线周期
    signal_period: 9             # 信号线周期
```

### Bollinger Bands 指标

```yaml
  bollinger_bands:
    period: 20                   # 周期
    std_dev: 2.0                 # 标准差倍数
```

### 综合评分权重

```yaml
  weights:
    ma: 0.3                      # MA 权重
    rsi: 0.25                    # RSI 权重
    macd: 0.25                   # MACD 权重
    volume: 0.2                  # 成交量权重
```

---

## 回测模块 (backtest)

```yaml
backtest:
  initial_cash: 1000000.0        # 初始资金
  commission_rate: 0.0003        # 佣金率（万三）
  stamp_duty_rate: 0.001         # 印花税率（千一）
  min_commission: 5.0            # 最低佣金
  trading_days_per_year: 252     # 每年交易日数
```

---

## Web 平台模块 (web)

### 控制面板配置

```yaml
web:
  control_panel:
    initial_cash:
      min_value: 10000           # 最小初始资金
      max_value: 100000000       # 最大初始资金
      default_value: 1000000     # 默认初始资金
      step: 10000                # 步长
    
    ma_short:
      min_value: 3               # 最小短期均线
      max_value: 20              # 最大短期均线
      default_value: 5           # 默认短期均线
    
    ma_long:
      min_value: 10              # 最小长期均线
      max_value: 60              # 最大长期均线
      default_value: 20          # 默认长期均线
    
    stop_loss:
      min_value: -20             # 最小止损
      max_value: -1              # 最大止损
      default_value: -8          # 默认止损
    
    take_profit:
      min_value: 5               # 最小止盈
      max_value: 50              # 最大止盈
      default_value: 20          # 默认止盈
    
    default_start_date: "2024-01-01"  # 默认开始日期
    default_end_date: "2024-03-31"    # 默认结束日期
```

---

## 通知模块 (notification)

### 钉钉通知

```yaml
notification:
  dingtalk:
    enabled: false               # 是否启用
    webhook_url: ""              # Webhook URL
    retry_times: 3               # 重试次数
    timeout: 10                  # 超时时间（秒）
```

### 飞书通知

```yaml
  feishu:
    enabled: false               # 是否启用
    webhook_url: ""              # Webhook URL
    retry_times: 3               # 重试次数
    timeout: 10                  # 超时时间（秒）
```

### 重试配置

```yaml
  retry:
    max_attempts: 3              # 最大重试次数
    wait_multiplier: 1           # 等待时间乘数
    wait_min: 1                  # 最小等待时间（秒）
    wait_max: 10                 # 最大等待时间（秒）
```

---

## 日志配置 (logging)

```yaml
logging:
  level: INFO                    # 日志级别
  format: json                   # 日志格式
  timezone: Asia/Shanghai        # 时区
```

---

## 全局配置

```yaml
timezone: Asia/Shanghai          # 全局时区
```

---

## 配置优先级

1. **代码中显式传入的参数** - 最高优先级
2. **配置文件中的参数** - 中等优先级
3. **代码中的默认值** - 最低优先级

### 示例

```python
# 优先级 1: 显式传入参数
engine = BacktestEngine(
    strategy=strategy,
    initial_cash=2000000.0,  # 使用这个值
)

# 优先级 2: 配置文件参数
# config/settings.yaml 中 backtest.initial_cash = 1000000.0

# 优先级 3: 代码默认值
# 如果以上都没有，使用默认值 1000000.0
```

---

## 环境变量

支持在配置文件中使用环境变量：

```yaml
data:
  providers:
    tushare:
      token: ${TUSHARE_TOKEN}  # 从环境变量读取
```

设置环境变量：

```bash
export TUSHARE_TOKEN="your_token_here"
```

---

## 配置最佳实践

1. **不要提交敏感信息** - Webhook URL、Token 等使用环境变量
2. **根据环境调整** - 开发环境和生产环境使用不同配置
3. **定期备份配置** - 保存配置文件的版本历史
4. **文档化修改** - 记录配置修改的原因和影响

---

## 配置验证

所有配置参数都会在运行时进行验证：

- 类型检查
- 范围检查
- 必填项检查

如果配置无效，系统会：
1. 记录错误日志
2. 使用默认值
3. 继续运行（不影响主流程）