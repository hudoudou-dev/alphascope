# AlphaScope AI 开发规范（Specify）

版本：1.0

---

# 1. 文档目标

本文件用于定义：

AI Agent 与开发者如何在 AlphaScope 项目中：

- 生成代码
- 修改代码
- 编写测试
- 扩展模块
- 保持架构一致性

目标：

- 保持长期可维护
- 保持 schema 稳定
- 保持模块边界清晰
- 保持 AI 可持续协作

---

# 2. AI 开发工作流

所有功能开发必须遵循：

1. 定义 Spec
2. 定义 Contract
3. 定义 Schema
4. 定义测试
5. 实现代码
6. 验证结果
7. 更新文档

禁止直接跳过规范阶段进行编码。

---

# 3. 模块生成规范

## 3.1 Data 模块规范

数据模块必须：

- 支持增量更新
- 支持 parquet 存储
- 支持 schema 校验
- 支持失败重试
- 隔离不同数据源逻辑

所有数据源必须继承：

```python
BaseDataProvider
```

---

## 3.2 Strategy 模块规范

所有策略必须继承：

```python
BaseStrategy
```

必须实现：

```python
prepare()
should_buy()
should_sell()
score_stock()
```

策略必须：

- 禁止未来函数
- 禁止直接写文件
- score 阶段保持无状态

---

## 3.3 Backtest 模块规范

回测模块必须：

- 严格按时间顺序执行
- 支持 deterministic replay
- 保存参数快照
- 保存交易历史

禁止：

- 修改原始数据
- 使用未来指标
- 跳过交易日校验

---

## 3.4 Indicator 模块规范

指标模块必须：

- 支持向量化计算
- 输出稳定
- 支持 rolling computation

建议：

- 使用 pandas DataFrame
- 避免副作用

---

## 3.5 Notification 模块规范

通知模块必须：

- 支持 retry
- 隔离 webhook provider
- 隐藏敏感信息

---

# 4. 配置规范

所有运行参数必须来自 YAML。

配置分类：

```yaml
data:
strategy:
backtest:
notification:
scheduler:
risk_control:
storage:
```

禁止隐藏配置。

---

# 5. Schema 规范

所有 schema 必须：

- 可版本化
- 向后兼容
- 定义 required fields
- 定义 nullable fields

---

# 6. 测试规范

所有生成模块必须包含：

- happy path test
- edge case test
- failure test

策略测试必须验证：

- 无未来函数
- 输出稳定
- score 可重复

---

# 7. 日志规范

所有生成模块必须记录：

- 开始执行
- 结束执行
- retry
- failure
- timing

禁止日志泄露敏感信息。

---

# 8. 性能规范

所有生成模块应：

- 使用 pandas 向量化
- 避免嵌套循环
- 减少内存复制

---

# 9. 文件组织规范

生成代码必须遵循：

```text
src/
├── data/
├── strategy/
├── backtest/
├── indicators/
├── notifier/
├── scheduler/
├── storage/
├── web/
└── tests/
```

---

# 10. 文档规范

所有模块必须包含：

- 模块说明
- 参数定义
- 输入输出 schema
- 示例代码

---

# 11. TRAE AI 协作规范

TRAE Agent 生成代码时必须：

优先读取：

```text
spec-kit/contracts/
spec-kit/schemas/
spec-kit/standards/
spec-kit/examples/
```

禁止：

- 自行猜测字段
- 自行新增 schema
- 自行修改 contract
- 自行发明命名

新增字段前必须同步更新：

- schema
- contract
- examples
- tests

---

# 12. AI 安全规则

AI 生成代码禁止：

- mutable global state
- silent exception
- hardcoded secret
- undocumented schema mutation

---

# 13. Pull Request 检查清单

所有提交必须验证：

- tests passed
- schema 未破坏
- typing 完整
- logging 完整
- 文档已同步