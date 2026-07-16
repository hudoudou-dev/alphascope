"""
选股策略类（多策略组合门面）

作为对外统一的选股入口，内部通过 StrategyCombiner 管理4套子策略：
- TrendStrategy:     趋势跟踪（权重30%）— ADX+MA+MACD+回调买点
- MomentumStrategy:  动量反转（权重25%）— 短期反转+多周期动量+RSI
- VolumePriceStrategy: 量价共振（权重25%）— 量比+换手率+量价相关+OBV
- QualityStrategy:   低波质量（权重20%）— 波动率+偏度+基本面

同时保留原有的筛选、风控等功能。
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.fundamental_indicators import FundamentalIndicators
from src.indicators.factor_normalizer import FactorNormalizer
from src.strategy.base_strategy import BaseStrategy
from src.strategy.risk_control import RiskControl, RiskControlConfig, MarketFilter
from src.strategy.strategy_combiner import (
    StrategyCombiner,
    WeightedAverageCombiner,
)
from src.strategy.sub_strategies import (
    TrendStrategy,
    MomentumStrategy,
    VolumePriceStrategy,
    QualityStrategy,
)
from src.strategy.regime import MarketRegime, RegimeDetector


@dataclass
class SelectionConfig:
    """选股策略配置"""
    # 市值与价格区间
    market_cap_min: float = 50.0  # 最小市值（亿元）
    market_cap_max: float = 20000.0  # 最大市值（亿元）
    price_min: float = 5.0  # 最小股价（元）
    price_max: float = 2000.0  # 最大股价（元）
    
    # 涨跌停配置
    limit_up_min: int = 0  # 最小涨停次数
    limit_down_max: int = 3  # 最大跌停次数
    limit_stat_period: int = 20  # 涨跌停统计周期（天）
    max_up_threshold: float = 10.0  # 最大涨幅阈值（%）
    max_down_threshold: float = -10.0  # 最大跌幅阈值（%）
    
    # 持仓配置
    initial_cash: float = 1000000.0  # 初始资金量（元）
    max_positions: int = 10  # 最大持仓股票数量
    top_n: int = 20  # 候选股票数量（Top-N）
    min_score_threshold: float = 50.0  # 最小评分阈值（中性=50，结合回调买点因子后50即可入选）
    
    # 交易频率控制
    cooldown_days: int = 5  # 冷却期（卖出后多少天内不能重新买入同一只股票）
    max_trades_per_day: int = 5  # 每天最大交易次数
    
    # ============ 4子策略融合权重（总和=100%） ============
    trend_weight: float = 35.0           # 趋势跟踪子策略权重（%）— TrendStrategy
    momentum_weight: float = 25.0        # 动量反转子策略权重（%）— MomentumStrategy
    volume_price_weight: float = 25.0    # 量价共振子策略权重（%）— VolumePriceStrategy
    quality_weight: float = 15.0         # 低波质量子策略权重（%）— QualityStrategy
    
    # ============ 风控配置 ============
    enable_risk_control: bool = True        # 是否启用风控
    enable_st_filter: bool = True           # ST股过滤
    enable_limit_filter: bool = True        # 涨停过滤
    
    # 横截面标准化 / 行情自适应（默认关闭，开启后改变打分相对性，不改变默认路径）
    cross_sectional_enabled: bool = False   # 横截面标准化打分
    regime_enabled: bool = False            # 行情自适应子策略权重
    
    @classmethod
    def from_config(cls) -> "SelectionConfig":
        """从配置文件读取选股策略配置"""
        config = config_loader.get("strategy", {}).get("selection", {})
        
        return cls(
            market_cap_min=config.get("market_cap_min", 50.0),
            market_cap_max=config.get("market_cap_max", 20000.0),
            price_min=config.get("price_min", 5.0),
            price_max=config.get("price_max", 2000.0),
            limit_up_min=config.get("limit_up_min", 0),
            limit_down_max=config.get("limit_down_max", 3),
            limit_stat_period=config.get("limit_stat_period", 20),
            max_up_threshold=config.get("max_up_threshold", 10.0),
            max_down_threshold=config.get("max_down_threshold", -10.0),
            initial_cash=config.get("initial_cash", 1000000.0),
            max_positions=config.get("max_positions", 10),
            top_n=config.get("top_n", 20),
            min_score_threshold=config.get("min_score_threshold", 50.0),
            cooldown_days=config.get("cooldown_days", 5),
            max_trades_per_day=config.get("max_trades_per_day", 5),
            # 4子策略融合权重
            trend_weight=config.get("trend_weight", 35.0),
            momentum_weight=config.get("momentum_weight", 25.0),
            volume_price_weight=config.get("volume_price_weight", 25.0),
            quality_weight=config.get("quality_weight", 15.0),
            # 风控配置
            enable_risk_control=config.get("enable_risk_control", True),
            enable_st_filter=config.get("enable_st_filter", True),
            enable_limit_filter=config.get("enable_limit_filter", True),
            # 横截面 / 行情自适应开关
            cross_sectional_enabled=config.get("cross_sectional_enabled", False),
            regime_enabled=config.get("regime_enabled", False),
        )
    
    def to_config_dict(self) -> dict[str, Any]:
        """转换为配置字典"""
        return {
            "market_cap_min": self.market_cap_min,
            "market_cap_max": self.market_cap_max,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "limit_up_min": self.limit_up_min,
            "limit_down_max": self.limit_down_max,
            "limit_stat_period": self.limit_stat_period,
            "max_up_threshold": self.max_up_threshold,
            "max_down_threshold": self.max_down_threshold,
            "initial_cash": self.initial_cash,
            "max_positions": self.max_positions,
            "top_n": self.top_n,
            "min_score_threshold": self.min_score_threshold,
            "cooldown_days": self.cooldown_days,
            "max_trades_per_day": self.max_trades_per_day,
            # 4子策略融合权重
            "trend_weight": self.trend_weight,
            "momentum_weight": self.momentum_weight,
            "volume_price_weight": self.volume_price_weight,
            "quality_weight": self.quality_weight,
            # 风控配置
            "enable_risk_control": self.enable_risk_control,
            "enable_st_filter": self.enable_st_filter,
            "enable_limit_filter": self.enable_limit_filter,
            # 横截面 / 行情自适应开关
            "cross_sectional_enabled": self.cross_sectional_enabled,
            "regime_enabled": self.regime_enabled,
        }


class SelectionStrategy(BaseStrategy):
    """选股策略类 — 多策略组合门面 + 风控过滤"""
    
    def __init__(self, config: SelectionConfig | None = None):
        super().__init__(strategy_name="SelectionStrategy")
        
        self.config = config or SelectionConfig.from_config()
        self.logger = get_logger(self.strategy_name)
        
        # 技术指标计算器（用于 prepare 统一计算全量指标）
        self._tech_indicators = TechnicalIndicators()
        # 基本面指标计算器（保留兼容）
        self._fund_indicators = FundamentalIndicators()
        
        # 风控组件
        risk_cfg = RiskControlConfig(
            enable_st_filter=self.config.enable_st_filter,
            enable_limit_filter=self.config.enable_limit_filter,
        )
        self._risk_control = RiskControl(risk_cfg)
        self._market_filter = MarketFilter()
        
        # ===== 多策略组合器（核心）=====
        # 直接使用 SelectionConfig 中的4子策略权重（由前端配置），归一化
        raw_weights = {
            "TrendStrategy": self.config.trend_weight,
            "MomentumStrategy": self.config.momentum_weight,
            "VolumePriceStrategy": self.config.volume_price_weight,
            "QualityStrategy": self.config.quality_weight,
        }
        total = sum(raw_weights.values())
        if total > 0:
            normalized_weights = {k: v / total for k, v in raw_weights.items()}
        else:
            normalized_weights = {k: 0.25 for k in raw_weights}
        
        self._combiner = StrategyCombiner(
            combiner=WeightedAverageCombiner(weights=normalized_weights),
            unified_data=True,
        )
        
        # 注册4套子策略
        self._combiner.add_strategy(TrendStrategy())
        self._combiner.add_strategy(MomentumStrategy())
        self._combiner.add_strategy(VolumePriceStrategy())
        self._combiner.add_strategy(QualityStrategy())
        
        # 子策略基础权重（归一化后，总和=1），供横截面/regime 重加权使用
        self._sub_weights: dict[str, float] = normalized_weights
        
        # 横截面标准化 / 行情自适应开关（默认关闭，向后兼容）
        cs_cfg = config_loader.get("strategy.cross_sectional", {})
        regime_cfg = config_loader.get("strategy.regime", {})
        self._cross_sectional_enabled = bool(self.config.cross_sectional_enabled)
        self._cs_method = cs_cfg.get("method", "zscore")
        self._regime_enabled = bool(self.config.regime_enabled)
        self._regime_detector = RegimeDetector(regime_cfg)
        self._last_regime: MarketRegime | None = None
        
        self.logger.info(
            "SelectionStrategy 初始化完成（多策略组合模式）",
            sub_strategies=[s.strategy_name for s in self._combiner.strategies],
            weights=normalized_weights,
        )
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据：复用基类统一计算全量技术指标（含 turn 换手率），按股票分组避免跨边界污染"""
        return super().prepare(df, compute_turn=True)
    
    def score_stock(self, code: str, stock_data: pd.DataFrame) -> float:
        """
        多策略组合综合评分
        
        通过 StrategyCombiner 融合4套子策略的评分：
        - TrendStrategy:     趋势跟踪
        - MomentumStrategy:  动量反转
        - VolumePriceStrategy: 量价共振
        - QualityStrategy:   低波质量
        
        返回：综合评分（0-100）
        """
        if stock_data.empty:
            return 50.0
        
        latest = stock_data.iloc[-1]
        close_price = latest.get("close_price", 0)
        if pd.isna(close_price) or close_price <= 0:
            return 50.0
        
        # 通过组合器计算多策略综合评分
        combined_score, self._last_detail_scores = self._combiner.score_stock_unified(
            code, stock_data
        )
        
        # 收集子策略完整度信息
        self._last_completeness_info = self._collect_completeness(code)
        
        # --- 长期强势股额外加分 ---
        ma20 = latest.get("ma20", 0)
        ma60 = latest.get("ma60", 0)
        if close_price > ma20 > ma60 > 0:
            combined_score += 3.0
        
        # --- 涨跌停惩罚 ---
        limit_penalty = self._calc_limit_penalty(stock_data)
        combined_score *= limit_penalty
        
        return max(0.0, min(100.0, combined_score))
    
    def get_last_detail_scores(self) -> dict[str, float]:
        """获取最近一次评分的子策略分项得分"""
        return getattr(self, "_last_detail_scores", {})
    
    def score_universe(
        self,
        stock_dfs: dict[str, pd.DataFrame],
        breadth: float | None = None,
        avg_vol: float | None = None,
    ) -> dict[str, dict]:
        """
        横截面两阶段打分（默认关闭，仅 cross_sectional/regime 开启时由选股路由调用）。

        Pass1：对 universe 中每只股票计算 4 子策略原始分项得分；
        Pass2（cross_sectional 开启）：按全市场横截面 zscore/rank 归一化到 0-100；
        （regime 开启）：依据 breadth/avg_vol 推导行情状态并切换子策略权重；
        最终按（自适应）权重融合为综合得分。

        Returns: {code: {"score", "detail"(归一化后子策略分), "completeness", "regime"}}
        """
        if not stock_dfs:
            return {}

        # Pass1：原始子策略分项得分
        raw: dict[str, dict[str, float]] = {}
        completeness_map: dict[str, dict] = {}
        for code, df in stock_dfs.items():
            _, detail = self._combiner.score_stock_unified(code, df)
            raw[code] = detail
            completeness_map[code] = self._combiner.get_completeness_info()

        # 权重（regime 自适应或基础权重）
        weights = dict(self._sub_weights)
        regime = None
        if self._regime_enabled and breadth is not None and avg_vol is not None:
            regime = self._regime_detector.detect(breadth, avg_vol)
            weights = self._regime_detector.regime_weights(regime, self._sub_weights)
            self._last_regime = regime

        # 横截面归一化
        if self._cross_sectional_enabled:
            normalizer = FactorNormalizer(method=self._cs_method)
            norm_raw = normalizer.normalize_universe(raw)
        else:
            norm_raw = raw

        results: dict[str, dict] = {}
        for code, detail in norm_raw.items():
            wsum = sum(weights.get(s, 0.0) for s in detail) or 1.0
            score = sum(detail[s] * weights.get(s, 0.0) for s in detail) / wsum
            results[code] = {
                "score": max(0.0, min(100.0, score)),
                "detail": detail,
                "completeness": completeness_map.get(code, {}),
                "regime": regime.value if regime else None,
            }
        return results
    
    def get_last_regime(self) -> str | None:
        """获取最近一次 score_universe 推导的行情状态（未开启 regime 时为 None）"""
        return self._last_regime.value if self._last_regime else None
    
    def _collect_completeness(self, code: str) -> dict:
        """收集所有子策略的完整度信息，并对数据不完整的情况发出警告"""
        info = self._combiner.get_completeness_info()
        
        # 检查是否有 incomplete 的策略
        incomplete_strategies = [
            name for name, c in info.items()
            if c.get("completeness") == "insufficient"
        ]
        partial_strategies = [
            name for name, c in info.items()
            if c.get("completeness") == "partial"
        ]
        
        if incomplete_strategies:
            self.logger.warning(
                "sub_strategies_with_insufficient_data",
                code=code,
                strategies=incomplete_strategies,
                details={name: info[name] for name in incomplete_strategies},
            )
        
        if partial_strategies:
            self.logger.warning(
                "sub_strategies_with_partial_data",
                code=code,
                strategies=partial_strategies,
                details={name: info[name] for name in partial_strategies},
            )
        
        return info
    
    def get_last_completeness(self) -> dict:
        """获取最近一次评分的子策略数据完整度信息"""
        return getattr(self, "_last_completeness_info", {})
    
    # ==================== 涨跌停惩罚 ====================
    
    def _calc_limit_penalty(self, stock_data: pd.DataFrame) -> float:
        """计算涨跌停惩罚系数（0-1），1表示无惩罚"""
        if stock_data.empty or self.config.limit_stat_period <= 0:
            return 1.0
        
        recent = stock_data.tail(self.config.limit_stat_period)
        if recent.empty or "pct_chg" not in recent.columns:
            return 1.0
        
        pct = recent["pct_chg"]
        limit_up_count = int(sum(pct >= self.config.max_up_threshold))
        limit_down_count = int(sum(pct <= self.config.max_down_threshold))
        
        # 跌停惩罚：每跌停一次扣5%，最多扣40%
        penalty = 1.0 - min(limit_down_count * 0.05, 0.4)
        
        # 涨停过多也可能是异常（连板风险），每涨停超过3次扣3%
        if limit_up_count > 3:
            penalty -= min((limit_up_count - 3) * 0.03, 0.15)
        
        return max(0.4, penalty)
    
    def filter_stock(self, daily_data: pd.Series, df: pd.DataFrame) -> bool:
        """
        筛选股票（集成风控过滤）
        
        筛选逻辑：
        1. 股价区间筛选
        2. 涨跌停配置筛选
        3. 市值区间筛选
        4. 风控过滤（涨停当日不可买、ST过滤）
        
        返回：是否通过筛选
        """
        close_price = daily_data.get("close_price", 0)
        
        # --- 股价区间筛选 ---
        if close_price < self.config.price_min or close_price > self.config.price_max:
            return False
        
        # --- 涨跌停配置筛选 ---
        if self.config.limit_stat_period > 0:
            recent_df = df.tail(self.config.limit_stat_period)
            if not recent_df.empty and "pct_chg" in recent_df.columns:
                pct_chg = recent_df["pct_chg"]
                limit_up_count = int(sum(pct_chg >= self.config.max_up_threshold))
                limit_down_count = int(sum(pct_chg <= self.config.max_down_threshold))
                
                if limit_up_count < self.config.limit_up_min:
                    return False
                if limit_down_count > self.config.limit_down_max:
                    return False
        
        # --- 市值区间筛选 ---
        market_cap = daily_data.get("total_mv", None)
        if market_cap is not None and not pd.isna(market_cap):
            cap_yi = float(market_cap) / 1e8  # 转为亿元
            if cap_yi < self.config.market_cap_min or cap_yi > self.config.market_cap_max:
                return False
        
        # --- 风控过滤 ---
        if self.config.enable_risk_control:
            code = daily_data.get("code", "")
            pct_chg_val = daily_data.get("pct_chg", None)
            result = self._risk_control.check_buy(
                code=str(code),
                price=close_price,
                pct_chg=float(pct_chg_val) if pct_chg_val is not None and not pd.isna(pct_chg_val) else None,
            )
            if not result.allowed:
                self.logger.debug(f"风控拦截: {code} - {result.reason}")
                return False
        
        return True
    
    def update_market_filter(self, all_data: pd.DataFrame) -> None:
        """使用全市场数据更新 MarketFilter（涨停/跌停/ST状态）"""
        self._market_filter.update_market_status(all_data)
    
    def update_st_list(self, st_codes: list[str]) -> None:
        """更新ST股列表"""
        self._risk_control.update_st_list(st_codes)
        self._market_filter.set_st_codes(st_codes)
    
    def get_strategy_info(self) -> dict[str, Any]:
        """获取策略信息"""
        weights = self._combiner.get_weights_info()
        return {
            "strategy_name": self.strategy_name,
            "mode": "multi_strategy_combined",
            "sub_strategies": [s.strategy_name for s in self._combiner.strategies],
            "sub_weights": weights,
            "config": self.config.to_config_dict(),
        }