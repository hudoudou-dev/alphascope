"""
行情状态（Market Regime）检测与自适应权重

依据全市场横截面统计（多头广度 breadth + 平均波动率 avg_vol）推断当前行情状态，
并据此动态切换 4 套子策略的融合权重：

- BULL（强牛）：趋势/动量主导 → 加重 Trend / Momentum
- TREND（温和趋势）：维持均衡，略偏趋势
- RANGE（震荡）：量价 / 质量占优
- BEAR（熊市）：防御为主 → 加重 Quality / 量价

不依赖单一宽基指数行情数据，直接从选股 universe 的横截面特征推导，
因此无需额外的指数数据下载。默认关闭。
"""

from enum import Enum
from typing import Any


class MarketRegime(str, Enum):
    BULL = "bull"
    TREND = "trend"
    RANGE = "range"
    BEAR = "bear"


# 各行情状态下的子策略融合权重（已归一化，总和=1）
_REGIME_WEIGHTS: dict[MarketRegime, dict[str, float]] = {
    MarketRegime.BULL: {
        "TrendStrategy": 0.45,
        "MomentumStrategy": 0.30,
        "VolumePriceStrategy": 0.15,
        "QualityStrategy": 0.10,
    },
    MarketRegime.TREND: {
        "TrendStrategy": 0.40,
        "MomentumStrategy": 0.25,
        "VolumePriceStrategy": 0.20,
        "QualityStrategy": 0.15,
    },
    MarketRegime.RANGE: {
        "TrendStrategy": 0.20,
        "MomentumStrategy": 0.20,
        "VolumePriceStrategy": 0.30,
        "QualityStrategy": 0.30,
    },
    MarketRegime.BEAR: {
        "TrendStrategy": 0.10,
        "MomentumStrategy": 0.15,
        "VolumePriceStrategy": 0.25,
        "QualityStrategy": 0.50,
    },
}


class RegimeDetector:
    def __init__(self, cfg: dict[str, Any] | None = None):
        cfg = cfg or {}
        # 多头广度阈值（close > ma20 的股票占比）
        self.breadth_bull = float(cfg.get("breadth_bull", 0.60))
        self.breadth_trend = float(cfg.get("breadth_trend", 0.50))
        self.breadth_bear = float(cfg.get("breadth_bear", 0.40))
        # 平均年化波动率阈值（hist_vol，小数）
        self.vol_high = float(cfg.get("vol_high", 0.50))
        self.vol_low = float(cfg.get("vol_low", 0.30))

    def detect(self, breadth: float, avg_vol: float) -> MarketRegime:
        """
        Args:
            breadth: 多头广度，close>ma20 的股票占比（0~1）
            avg_vol: 全市场平均年化历史波动率（小数，如 0.4 表示 40%）
        """
        if breadth >= self.breadth_bull and avg_vol < self.vol_high:
            return MarketRegime.BULL
        if breadth >= self.breadth_trend:
            return MarketRegime.TREND
        if breadth <= self.breadth_bear:
            return MarketRegime.BEAR
        return MarketRegime.RANGE

    def regime_weights(
        self, regime: MarketRegime, base: dict[str, float]
    ) -> dict[str, float]:
        """返回某行情状态下的子策略权重；未知状态退回 base 权重。"""
        return dict(_REGIME_WEIGHTS.get(regime, base))
