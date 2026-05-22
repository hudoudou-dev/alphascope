# AlphaScope

A股量化选股与回测平台

## 项目结构

```
alphascope/
├── config/              # 配置文件
│   └── settings.yaml
├── docs/                # 文档
├── examples/            # 示例代码
├── specs/               # 规范文档
├── src/                 # 源代码
│   ├── core/           # 核心模块
│   │   ├── config.py   # 配置加载
│   │   └── logger.py   # 日志系统
│   └── data/           # 数据模块
│       ├── schema.py   # 数据校验
│       └── providers/  # 数据提供者
│           ├── base_data_provider.py
│           ├── akshare_provider.py
│           ├── baostock_provider.py
│           └── tushare_provider.py
└── tests/              # 测试代码
    └── data/
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
pytest tests/ -v
```

### 使用示例

```python
from datetime import datetime
from src.data.providers.akshare_provider import AKShareProvider

# 初始化
provider = AKShareProvider(storage_path="./data")

# 下载数据
df = provider.download_and_save(
    "600000.SH",
    datetime(2024, 1, 1),
    datetime(2024, 1, 31)
)

print(df.head())
```

## 功能特性

- ✅ 多数据源支持（AKShare、BaoStock、Tushare）
- ✅ 自动数据验证
- ✅ Parquet 存储（Snappy 压缩）
- ✅ 增量更新
- ✅ 自动重试
- ✅ 结构化日志
- ✅ 时区支持（Asia/Shanghai）
- ✅ 未来数据检查
- ✅ 完整的单元测试

## 开发规范

详见 [specs/constitution.md](specs/constitution.md)

## 许可证

MIT
