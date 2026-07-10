# AlphaScope 开发路线图

## 已完成功能

### Phase 1 - 核心链路打通 ✅
- [x] 集成交易日历到回测引擎
- [x] 添加滑点模拟
- [x] 打通下载→回测数据流

### Phase 2 - 系统完整性补齐 ✅
- [x] 创建 Pipeline 编排层
- [x] 实现调度系统

### Phase 3 - 多策略引擎升级 ✅
- [x] 4 套子策略并行打分（Trend/Momentum/VolumePrice/Quality）
- [x] 加权平均融合
- [x] 缺失数据处理（redistribute/neutral/penalize/exclude）
- [x] 公共 prepare/score_stock 模板化（去重）
- [x] 基本面因子接入（PE/PB，优雅降级）
- [x] 横截面标准化（z-score/rank，默认关闭）
- [x] 行情自适应权重（BULL/TREND/RANGE/BEAR，默认关闭）
- [x] 统一 min_score_threshold 单一来源
- [x] 删除死代码（VotingCombiner、旧评分函数、legacy 配置字段）

### Phase 4 - 架构与质量提升 ✅
- [x] 完善风控模块（ST/涨停/行业集中度）
- [x] 修复 YAML 环境变量替换
- [x] 实现数据清理机制
- [x] 创建 DataManager 统一入口
- [x] 实现策略插件注册机制
- [x] 回测结果持久化与对比
- [x] 实现策略组合（加权融合）
- [x] 添加基准对比
- [x] 清理死代码
- [x] 补充空文档
- [x] FastAPI + Vue.js 前后端分离

## 近期计划

### Phase 5 - 调度与自动化
- [ ] Pipeline 编排层（交易日→数据→策略→回测→通知）
- [ ] APScheduler 调度系统
- [ ] 通知系统接入核心流程

### Phase 6 - 数据与监控
- [ ] 数据质量仪表盘
- [ ] 实时数据接入
- [ ] 数据清理机制完善

## 远期规划

### Phase 7 - 策略增强
- [ ] ROE/资产负债率等财报基本面因子
- [ ] 因子 IC/IR 评估体系
- [ ] 超参自动寻优（IC 驱动权重/阈值）
- [ ] 行业/板块维度

### Phase 8 - 工程化
- [ ] 异步任务队列（Celery + Redis）
- [ ] Redis 缓存层
- [ ] 集成测试补充
- [ ] 服务层抽象

## 版本规划

### v2.1.0 (近期)
- Pipeline 编排 + 调度系统
- 通知系统接入
- 数据质量监控

### v2.2.0 (中期)
- 财报基本面因子
- 因子 IC/IR 评估
- 异步任务队列

### v3.0.0 (远期)
- 超参自动寻优
- Redis 缓存层
- 分布式回测支持
