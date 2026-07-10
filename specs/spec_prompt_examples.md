# AlphaScope Spec Prompt 示例

本文档收集基于当前项目规范的 AI Prompt 示例，用于指导 AI Agent 生成符合规范的代码。

---

## 场景1：生成子策略

基于以下规范生成一个新的子策略：

- specs/constitution.md
- specs/specify.md
- specs/contracts/strategy_contract.md
- specs/schemas/strategy.schema.yaml

要求：
1. 继承 BaseStrategy
2. 实现 `build_factor_scores()`，返回因子字典 + 权重
3. 禁止 future leakage
4. 支持 YAML 参数配置（所有超参从 `config/settings.yaml` 的 `strategy.sub_strategies.*` 读取）
5. 包含完整 typing
6. 自动生成 pytest
7. 输出 deterministic score (0-100)
8. 使用 pandas vectorized computation
9. 缺失因子通过 `_redistribute_scores` 优雅降级

同时生成：
- 策略文件（放入 `src/strategy/`）
- 测试文件
- 配置示例（更新 settings.yaml）

---

## 场景2：生成 Data Provider

请阅读：
- specs/constitution.md
- specs/specify.md
- specs/contracts/data_contract.md
- specs/schemas/data.schema.yaml

实现新的数据提供者：

要求：
1. 继承 BaseDataProvider
2. 支持：日线数据下载、增量更新、parquet 持久化（`./data/raw/`）
3. 使用 pyarrow + snappy
4. 必须进行 schema validation
5. 支持 retry
6. 支持 structured logging
7. 不允许 future date
8. 兼容 Asia/Shanghai timezone
9. 如有基本面数据接口，实现类似 `get_daily_basic_history()` + `_merge_daily_basic()` 的合并逻辑

同时生成：
- pytest 单元测试
- mock data fixture

禁止：
- hardcoded config
- silent exception
- mutable global state

---

## 场景3：代码审查

请 review 当前策略模块。

重点检查：
1. 是否违反：constitution.md、specify.md、strategy_contract.md
2. 是否存在：future leakage、mutable global state、schema drift、hidden side effect
3. 是否符合：structured logging、typing、deterministic output
4. 子策略是否正确实现 build_factor_scores 接口
5. 缺失数据处理是否符合配置的模式

请输出：
- 风险等级
- 问题列表
- 修复建议
- 推荐 patch

---

## 场景4：策略配置管理

请基于当前架构，分析以下需求：

"选股策略配置页面的参数需要与 config/settings.yaml 文件打通与同步"

分析：
1. 当前 SelectionConfig 是否已实现 from_config() / to_config_dict()
2. Web 前端 StrategyConfigView.vue 是否已对接 API
3. 配置修改后是否需要重启服务
4. 配置版本管理策略

---

## 策略清单

| 策略名称 | 类名 | 说明 |
|---------|------|------|
| 趋势跟踪 | TrendStrategy | ADX + MA排列 + MACD + 回调买点 |
| 动量反转 | MomentumStrategy | 短期反转 + 多周期动量(10/20/60) + RSI |
| 量价共振 | VolumePriceStrategy | 量比 + 换手率 + 量价相关 + OBV + 缩量止跌 |
| 低波质量 | QualityStrategy | 波动率 + 偏度 + 下行风险 + 基本面(PE/PB) |

---

## 高级 Prompt：架构分析

请基于当前：
- contracts/
- schemas/
- constitution.md
- specify.md

分析当前系统是否适合：

"多策略并行回测"

请输出：
1. 当前架构瓶颈
2. schema 是否需要扩展
3. strategy contract 是否足够
4. 多策略并行对 replay consistency 的风险
5. multiprocessing 风险
6. parquet IO 风险

并输出推荐方案。
