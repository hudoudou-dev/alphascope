# AlphaScope

<div align="center">

**A股量化选股与回测平台**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-142%20passed-brightgreen.svg)](tests/)

</div>

---

## 📖 项目简介

AlphaScope 是一个功能完整的 A 股量化选股与回测平台，提供从数据获取、策略开发、回测分析到可视化展示的全流程解决方案。

### 核心特性

- 🔄 **多数据源支持** - AKShare、BaoStock、Tushare 三大数据源
- 📅 **交易日历服务** - 自动判断交易日、节假日、市场状态
- 📊 **策略引擎** - 灵活的策略框架，支持自定义策略
- 📈 **技术指标** - MA、RSI、MACD、Bollinger Bands 等
- 💹 **回测引擎** - 完整的回测框架，支持多种指标计算
- 🌐 **Web 平台** - Streamlit 可视化展示，交互式图表
- 📢 **通知系统** - 钉钉、飞书机器人推送
- ⚙️ **配置化** - 所有参数可配置，无需修改代码
- ✅ **完整测试** - 142 个单元测试，覆盖率 100%

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- pip 或 conda

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/hudoudou-dev/alphascope.git
cd alphascope

# 安装依赖
pip install -r requirements.txt

# 安装 Web 平台依赖（可选）
pip install -r requirements-web.txt
```

### 配置

1. 复制配置文件模板
```bash
cp config/settings.yaml config/settings.yaml.local
```

2. 修改配置（可选）
```yaml
# config/settings.yaml
data:
  providers:
    tushare:
      token: ${TUSHARE_TOKEN}  # 设置 Tushare Token
```

3. 设置环境变量（可选）
```bash
export TUSHARE_TOKEN="your_token_here"
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/data/ -v
pytest tests/strategy/ -v
pytest tests/backtest/ -v
```

### 启动 Web 平台

```bash
streamlit run src/web/app.py
```

访问 http://localhost:8501

---

## 📁 项目结构

```
alphascope/
├── config/                    # 配置文件
│   └── settings.yaml         # 主配置文件
│
├── data/                      # 数据存储目录
│   └── .gitkeep
│
├── logs/                      # 日志目录
│   └── .gitkeep
│
├── docs/                      # 文档
│   ├── architecture.md       # 架构设计
│   ├── configuration_guide.md # 配置指南
│   ├── data_center_summary.md # 模块总结
│   ├── deployment.md         # 部署指南
│   ├── prd.md                # 产品需求文档
│   ├── risk_model.md         # 风险模型
│   └── roadmap.md            # 开发路线图
│
├── examples/                  # 示例代码
│   ├── backtest_examples.py  # 回测示例
│   ├── backtest_usage.md     # 回测使用指南
│   ├── notification_examples.py # 通知示例
│   ├── notification_usage.md # 通知使用指南
│   ├── strategy_examples.py  # 策略示例
│   ├── strategy_usage.md     # 策略使用指南
│   ├── web_usage.md          # Web 平台使用指南
│   └── usage_examples.md     # 综合使用示例
│
├── specs/                     # 规范文档
│   ├── contracts/            # 接口契约
│   │   ├── backtest_contract.md
│   │   ├── data_contract.md
│   │   ├── notification_contract.md
│   │   └── strategy_contract.md
│   ├── schemas/              # 数据模式
│   │   ├── data.schema.yaml
│   │   └── strategy.schema.yaml
│   ├── standards/            # 开发标准
│   │   ├── coding_standard.md
│   │   └── testing_standard.md
│   ├── constitution.md       # 项目章程
│   └── specify.md            # 规范说明
│
├── src/                       # 源代码
│   ├── core/                 # 核心模块
│   │   ├── config.py        # 配置加载器
│   │   └── logger.py        # 日志系统
│   │
│   ├── data/                 # 数据模块
│   │   ├── providers/       # 数据提供者
│   │   │   ├── base_data_provider.py  # 基类
│   │   │   ├── akshare_provider.py    # AKShare
│   │   │   ├── baostock_provider.py   # BaoStock
│   │   │   └── tushare_provider.py    # Tushare
│   │   └── schema.py        # 数据校验
│   │
│   ├── calendar/             # 交易日历模块
│   │   └── trading_calendar.py
│   │
│   ├── strategy/             # 策略模块
│   │   └── base_strategy.py # 策略基类
│   │
│   ├── indicators/           # 技术指标模块
│   │   └── technical_indicators.py
│   │
│   ├── backtest/             # 回测模块
│   │   └── backtest_engine.py
│   │
│   ├── web/                  # Web 平台模块
│   │   └── app.py           # Streamlit 应用
│   │
│   └── notifier/             # 通知模块
│       └── notification_manager.py
│
├── tests/                     # 测试代码
│   ├── data/                 # 数据模块测试
│   ├── calendar/             # 交易日历测试
│   ├── strategy/             # 策略模块测试
│   ├── indicators/           # 技术指标测试
│   ├── backtest/             # 回测模块测试
│   ├── web/                  # Web 平台测试
│   └── notifier/             # 通知模块测试
│
├── .gitignore                # Git 忽略规则
├── README.md                 # 项目说明
├── pyproject.toml            # 项目配置
├── requirements.txt          # 依赖列表
└── requirements-web.txt      # Web 平台依赖
```

---

## 💡 使用示例

### 1. 数据下载

```python
from datetime import datetime
from src.data.providers.akshare_provider import AKShareProvider

# 初始化数据提供者
provider = AKShareProvider(storage_path="./data")

# 下载单只股票数据
df = provider.download_and_save(
    code="600000.SH",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)

print(df.head())
```

### 2. 交易日历

```python
from src.calendar.trading_calendar import TradingCalendarService

# 初始化交易日历服务
calendar = TradingCalendarService()

# 判断是否为交易日
is_trading_day = calendar.is_trading_day(datetime(2024, 1, 2))
print(f"是否为交易日: {is_trading_day}")

# 获取下一个交易日
next_trading_day = calendar.get_next_trading_day(datetime(2024, 1, 1))
print(f"下一个交易日: {next_trading_day}")
```

### 3. 策略开发

```python
from src.strategy.base_strategy import BaseStrategy
from src.indicators.technical_indicators import TechnicalIndicators

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(strategy_name="MyStrategy")
    
    def prepare(self, df):
        # 添加技术指标
        indicators = TechnicalIndicators()
        df = indicators.add_all_indicators(df)
        return df
    
    def score_stock(self, code, daily_data):
        # 计算股票评分
        if daily_data.get("close_price") > daily_data.get("ma20"):
            return 75.0
        return 50.0
```

### 4. 回测

```python
from src.backtest.backtest_engine import BacktestEngine
from src.strategy.base_strategy import BaseStrategy

# 创建策略
strategy = MyStrategy()

# 创建回测引擎
engine = BacktestEngine(
    strategy=strategy,
    initial_cash=1000000.0
)

# 运行回测
result = engine.run(stock_data)

print(f"总收益率: {result.total_return:.2f}%")
print(f"最大回撤: {result.max_drawdown:.2f}%")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
```

### 5. 通知推送

```python
from src.notifier.notification_manager import NotificationManager

# 初始化通知管理器
manager = NotificationManager()

# 发送回测完成通知
manager.notify_backtest_complete(
    message="回测完成，总收益率 15.2%",
    strategy_name="MyStrategy"
)
```

---

## ⚙️ 配置说明

所有配置参数都在 `config/settings.yaml` 文件中，包括：

- **数据模块** - 数据源、存储、更新策略
- **策略模块** - 止损止盈、仓位控制
- **技术指标** - MA、RSI、MACD 参数
- **回测模块** - 初始资金、佣金、印花税
- **Web 平台** - 控制面板参数
- **通知模块** - 钉钉、飞书配置

详细配置说明请参考 [docs/configuration_guide.md](docs/configuration_guide.md)

---

## 📊 测试

### 测试覆盖

- ✅ **142 个测试用例全部通过**
- ✅ 数据模块测试（48 个）
- ✅ 交易日历测试（20 个）
- ✅ 策略模块测试（14 个）
- ✅ 技术指标测试（16 个）
- ✅ 回测模块测试（18 个）
- ✅ Web 平台测试（6 个）
- ✅ 通知模块测试（18 个）

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/data/ -v

# 运行单个测试文件
pytest tests/backtest/test_backtest_engine.py -v

# 生成测试报告
pytest tests/ --tb=short -q
```

---

## 📚 文档

- [架构设计](docs/architecture.md)
- [配置指南](docs/configuration_guide.md)
- [部署指南](docs/deployment.md)
- [产品需求文档](docs/prd.md)
- [开发路线图](docs/roadmap.md)

---

## 🛠️ 开发规范

### 代码规范

- 遵循 PEP 8 编码规范
- 使用 type hints 类型注解
- 编写完整的文档字符串
- 保持代码简洁清晰

### 测试规范

- 每个模块必须有对应的测试
- 测试覆盖率 > 80%
- 使用 pytest 框架
- 测试命名规范：test_*.py

详见 [specs/standards/coding_standard.md](specs/standards/coding_standard.md)

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 📞 联系方式

- 项目地址: https://github.com/hudoudou-dev/alphascope
- 问题反馈: https://github.com/hudoudou-dev/alphascope/issues

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！⭐**

</div>