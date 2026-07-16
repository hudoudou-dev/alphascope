"""
子策略模块：4套独立策略并行打分

- TrendStrategy:     趋势跟踪策略（权重30%）— ADX+MA+MACD+中期趋势+回调买点
- MomentumStrategy:  动量反转策略（权重25%）— 短期反转+多周期动量+RSI
- VolumePriceStrategy: 量价共振策略（权重25%）— 量比+换手率+量价相关+OBV
- QualityStrategy:   低波动质量策略（权重20%）— 波动率+偏度+基本面

每套策略继承 BaseStrategy，可直接被 StrategyCombiner 组合使用。
所有策略超参统一收敛到 config/settings.yaml 中管理。
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.fundamental_indicators import FundamentalIndicators
from src.strategy.base_strategy import BaseStrategy


# ==================== 子策略公共配置 ====================

@dataclass
class SubStrategyWeights:
    """子策略融合权重配置，统一从 config 加载"""

    # ---- 融合权重 ----
    trend: float = 30.0
    momentum: float = 25.0
    volume_price: float = 25.0
    quality: float = 20.0

    # ---- 策略A：趋势跟踪 ----
    trend_cfg: dict = field(default_factory=dict)

    # ---- 策略B：动量反转 ----
    momentum_cfg: dict = field(default_factory=dict)

    # ---- 策略C：量价共振 ----
    volume_price_cfg: dict = field(default_factory=dict)

    # ---- 策略D：低波动质量 ----
    quality_cfg: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls) -> "SubStrategyWeights":
        cfg = config_loader.get("strategy", {}).get("sub_strategies", {})
        return cls(
            trend=cfg.get("trend_weight", 30.0),
            momentum=cfg.get("momentum_weight", 25.0),
            volume_price=cfg.get("volume_price_weight", 25.0),
            quality=cfg.get("quality_weight", 20.0),
            trend_cfg=cfg.get("trend", {}),
            momentum_cfg=cfg.get("momentum", {}),
            volume_price_cfg=cfg.get("volume_price", {}),
            quality_cfg=cfg.get("quality", {}),
        )

    def normalize(self) -> dict[str, float]:
        raw = {
            "trend": max(0, self.trend),
            "momentum": max(0, self.momentum),
            "volume_price": max(0, self.volume_price),
            "quality": max(0, self.quality),
        }
        total = sum(raw.values())
        if total == 0:
            return {"trend": 30, "momentum": 25, "volume_price": 25, "quality": 20}
        return {k: v / total * 100 for k, v in raw.items()}


# ---- 公共辅助函数 ----

def _trend_background(latest: pd.Series) -> tuple[bool, bool]:
    """判断长/中期趋势背景"""
    close = latest.get("close_price", 0)
    ma20 = latest.get("ma20", 0)
    ma60 = latest.get("ma60", 0)
    long_bull = (close > ma20 > 0) and (ma20 > ma60 > 0) if ma20 > 0 and ma60 > 0 else False
    mid_bull = (close > ma60 > 0) if ma60 > 0 else False
    return long_bull, mid_bull


def _get_cfg(path: str, default: Any = None) -> Any:
    """便捷：从 sub_strategies 节点下按点分路径读取配置值"""
    return config_loader.get(f"strategy.sub_strategies.{path}", default)


# ==================== 策略A：趋势跟踪策略 ====================

class TrendStrategy(BaseStrategy):
    """
    趋势跟踪策略（权重30%）
    
    专注：趋势明确的股票，适合单边市
    因子：ADX趋势强度 + MA排列 + MACD信号 + 中期趋势 + 回调买点
    """

    def __init__(self):
        super().__init__(strategy_name="TrendStrategy")
        self.logger = get_logger(self.strategy_name)
        self._tech_indicators = TechnicalIndicators()
        self._load_config()

    def _load_config(self):
        """从配置文件加载所有超参，硬编码值仅作为兜底默认值"""
        c = _get_cfg("trend", {})

        # ADX 阈值
        self._adx_strong = c.get("adx_strong_threshold", 25.0)
        self._adx_weak = c.get("adx_weak_threshold", 20.0)

        # ADX 场景评分
        self._adx_strong_up = c.get("adx_strong_up", 80.0)
        self._adx_strong_down = c.get("adx_strong_down", 30.0)
        self._adx_moderate_up = c.get("adx_moderate_up", 65.0)
        self._adx_moderate_down = c.get("adx_moderate_down", 40.0)
        self._adx_weak_neutral = c.get("adx_weak_neutral", 50.0)

        # 子因子权重
        self._w_adx = c.get("adx_weight", 0.30)
        self._w_ma = c.get("ma_weight", 0.30)
        self._w_macd = c.get("macd_weight", 0.20)
        self._w_pullback = c.get("pullback_weight", 0.20)

        # MA 排列评分
        self._ma_perfect_bull = c.get("ma_perfect_bull", 85.0)
        self._ma_partial_bull = c.get("ma_partial_bull", 75.0)
        self._ma_short_bull = c.get("ma_short_bull", 65.0)
        self._ma_perfect_bear = c.get("ma_perfect_bear", 25.0)
        self._ma_partial_bear = c.get("ma_partial_bear", 35.0)
        self._ma_short_bear = c.get("ma_short_bear", 45.0)
        self._ma_above_ma5_not_bull = c.get("ma_above_ma5_not_bull", 47.0)
        self._ma_below_ma5_ma_still_up = c.get("ma_below_ma5_ma_still_up", 58.0)
        self._ma_above_ma20 = c.get("ma_above_ma20", 55.0)
        self._ma_below_ma20 = c.get("ma_below_ma20", 45.0)
        self._ma_default_neutral = c.get("ma_default_neutral", 50.0)

        # MACD 信号评分
        self._macd_base = c.get("macd_base", 50.0)
        self._macd_golden_cross_bonus = c.get("macd_golden_cross_bonus", 18.0)
        self._macd_dead_cross_penalty = c.get("macd_dead_cross_penalty", -15.0)
        self._macd_dead_strong_bull_discount = c.get("macd_dead_strong_bull_discount", 0.35)
        self._macd_dead_mid_bull_discount = c.get("macd_dead_mid_bull_discount", 0.60)
        self._macd_hist_positive = c.get("macd_hist_positive", 3.0)
        self._macd_hist_negative_bull = c.get("macd_hist_negative_bull", -2.0)
        self._macd_hist_negative_weak = c.get("macd_hist_negative_weak", -4.0)

        # 回调买点评分
        self._pullback_no_pullback = c.get("pullback_no_pullback", 50.0)
        self._pullback_no_pullback_bull = c.get("pullback_no_pullback_bull", 65.0)
        self._pullback_no_pullback_bear = c.get("pullback_no_pullback_bear", 45.0)
        self._pullback_ma_perfect = c.get("pullback_ma_perfect", 82.0)
        self._pullback_long_bull = c.get("pullback_long_bull", 75.0)
        self._pullback_mid_bull = c.get("pullback_mid_bull", 62.0)
        self._pullback_below_ma60 = c.get("pullback_below_ma60", 30.0)
        self._pullback_other = c.get("pullback_other", 45.0)

    def build_factor_scores(
        self, code: str, stock_data: pd.DataFrame
    ) -> tuple[dict[str, tuple[float, bool]], dict[str, float]]:
        latest = stock_data.iloc[-1]
        close_price = latest.get("close_price", 0)
        long_bull, mid_bull = _trend_background(latest)

        adx_score, adx_missing = self._score_adx(latest)
        ma_score, ma_missing = self._score_ma(close_price, latest)
        macd_score, macd_missing = self._score_macd(latest, long_bull, mid_bull)
        pullback_score, pullback_missing = self._score_pullback(close_price, latest, long_bull, mid_bull)

        factor_scores = {
            "adx": (adx_score, adx_missing),
            "ma": (ma_score, ma_missing),
            "macd": (macd_score, macd_missing),
            "pullback": (pullback_score, pullback_missing),
        }
        weights = {
            "adx": self._w_adx,
            "ma": self._w_ma,
            "macd": self._w_macd,
            "pullback": self._w_pullback,
        }
        return factor_scores, weights

    def _score_adx(self, latest: pd.Series) -> tuple[float, bool]:
        adx = latest.get("adx", np.nan)
        pdi = latest.get("pdi", np.nan)
        mdi = latest.get("mdi", np.nan)

        if pd.isna(adx) or pd.isna(pdi) or pd.isna(mdi):
            return self._adx_weak_neutral, True

        if adx >= self._adx_strong:
            return (self._adx_strong_up, False) if pdi > mdi else (self._adx_strong_down, False)
        elif adx >= self._adx_weak:
            return (self._adx_moderate_up, False) if pdi > mdi else (self._adx_moderate_down, False)
        else:
            return self._adx_weak_neutral, False

    def _score_ma(self, close: float, latest: pd.Series) -> tuple[float, bool]:
        ma5 = latest.get("ma5", 0)
        ma10 = latest.get("ma10", 0)
        ma20 = latest.get("ma20", 0)
        ma60 = latest.get("ma60", 0)

        if close <= 0 or ma5 <= 0 or ma10 <= 0:
            return self._ma_default_neutral, True

        if close > ma5 > ma10 > ma20 > ma60:
            return self._ma_perfect_bull, False
        elif close > ma5 > ma10 > ma20:
            return self._ma_partial_bull, False
        elif close > ma5 > ma10:
            return self._ma_short_bull, False
        elif close < ma5 < ma10 < ma20 < ma60:
            return self._ma_perfect_bear, False
        elif close < ma5 < ma10 < ma20:
            return self._ma_partial_bear, False
        elif close < ma5 < ma10:
            return self._ma_short_bear, False

        if close > ma5 and not (ma5 > ma10):
            return self._ma_above_ma5_not_bull, False
        elif close < ma5 and ma5 > ma10:
            return self._ma_below_ma5_ma_still_up, False
        elif close > ma20:
            return self._ma_above_ma20, False
        elif close < ma20:
            return self._ma_below_ma20, False
        return self._ma_default_neutral, False

    def _score_macd(self, latest: pd.Series, long_bull: bool, mid_bull: bool) -> tuple[float, bool]:
        macd = latest.get("macd", np.nan)
        macd_signal = latest.get("macd_signal", np.nan)
        macd_hist = latest.get("macd_hist", np.nan)

        if pd.isna(macd) or pd.isna(macd_signal):
            return self._macd_base, True

        score = self._macd_base
        if macd > macd_signal:
            score += self._macd_golden_cross_bonus
        else:
            if long_bull:
                score += self._macd_dead_cross_penalty * self._macd_dead_strong_bull_discount
            elif mid_bull:
                score += self._macd_dead_cross_penalty * self._macd_dead_mid_bull_discount
            else:
                score += self._macd_dead_cross_penalty

        if not pd.isna(macd_hist):
            score += self._macd_hist_positive if macd_hist > 0 else (
                self._macd_hist_negative_bull if long_bull else self._macd_hist_negative_weak
            )
        return score, False

    def _score_pullback(self, close: float, latest: pd.Series,
                        long_bull: bool, mid_bull: bool) -> tuple[float, bool]:
        ma5 = latest.get("ma5", 0)
        ma10 = latest.get("ma10", 0)
        ma20 = latest.get("ma20", 0)
        ma60 = latest.get("ma60", 0)

        # NaN 或无效均线 → 无法判断回调，标记缺失
        if pd.isna(ma5) or pd.isna(ma10) or ma5 <= 0 or ma10 <= 0:
            return self._pullback_no_pullback, True

        if close >= ma5:
            # P1-S4: 不回调节场景区分
            ma_bullish = ma5 > ma10 > ma20 > ma60 > 0
            ma_bearish = close < ma5 < ma10 < ma20 < ma60
            if ma_bullish:
                return self._pullback_no_pullback_bull, False   # 强势拉升，无需回调
            elif ma_bearish:
                return self._pullback_no_pullback_bear, False   # 下跌中反弹，有风险
            return self._pullback_no_pullback, False            # 中性

        ma_bullish = ma5 > ma10 > ma20 > ma60 > 0

        if ma_bullish:
            return self._pullback_ma_perfect, False
        elif long_bull:
            return self._pullback_long_bull, False
        elif mid_bull:
            return self._pullback_mid_bull, False
        elif close < ma60:
            return self._pullback_below_ma60, False
        return self._pullback_other, False


# ==================== 策略B：动量反转策略 ====================

class MomentumStrategy(BaseStrategy):
    """
    动量反转策略（权重25%）
    
    专注：短期超跌反弹 + 中期动量向上，适合震荡市
    因子：短期反转(5日) + 多周期动量 + RSI + 动量加速度
    """

    def __init__(self):
        super().__init__(strategy_name="MomentumStrategy")
        self.logger = get_logger(self.strategy_name)
        self._tech_indicators = TechnicalIndicators()
        self._load_config()

    def _load_config(self):
        c = _get_cfg("momentum", {})

        # 子因子权重（短期反转已降低权重，多周期动量提升）
        self._w_short_rev = c.get("short_reversal_weight", 0.20)
        self._w_multi_mom = c.get("multi_momentum_weight", 0.50)
        self._w_rsi = c.get("rsi_weight", 0.30)

        # 多周期动量内层权重
        self._w_mom10 = c.get("mom10_weight", 0.40)
        self._w_mom20 = c.get("mom20_weight", 0.35)
        self._w_mom60 = c.get("mom60_weight", 0.25)

        # 短期反转评分
        self._sr_severe_oversold = c.get("short_rev_severe_oversold", 78.0)
        self._sr_oversold = c.get("short_rev_oversold", 72.0)
        self._sr_clear_oversold = c.get("short_rev_clear_oversold", 65.0)
        self._sr_mild_oversold = c.get("short_rev_mild_oversold", 58.0)
        self._sr_slight_fall = c.get("short_rev_slight_fall", 52.0)
        self._sr_slight_rise = c.get("short_rev_slight_rise", 48.0)
        self._sr_overbought = c.get("short_rev_overbought", 40.0)
        self._sr_hot = c.get("short_rev_hot", 30.0)
        self._sr_extreme_hot = c.get("short_rev_extreme_hot", 22.0)

        # 短期反转阈值
        self._sr_b_severe = c.get("short_rev_severe_bound", -15)
        self._sr_b_oversold = c.get("short_rev_oversold_bound", -10)
        self._sr_b_clear = c.get("short_rev_clear_bound", -7)
        self._sr_b_mild = c.get("short_rev_mild_bound", -3)
        self._sr_b_neutral = c.get("short_rev_neutral_bound", 0)
        self._sr_b_slight_rise = c.get("short_rev_slight_rise_bound", 5)
        self._sr_b_overbought = c.get("short_rev_overbought_bound", 10)
        self._sr_b_hot = c.get("short_rev_hot_bound", 20)

        # 10日动量（单调递增：涨幅越大分越高）
        self._m10_extreme_up = c.get("mom10_extreme_up", 82.0)
        self._m10_strong_up = c.get("mom10_strong_up", 70.0)
        self._m10_moderate_up = c.get("mom10_moderate_up", 58.0)
        self._m10_slight_down = c.get("mom10_slight_down", 45.0)
        self._m10_down = c.get("mom10_down", 30.0)
        self._m10_t = c.get("mom10_thresholds", [15, 5, 0, -5])

        # 20日动量（单调递增：涨幅越大分越高）
        self._m20_extreme_up = c.get("mom20_extreme_up", 85.0)
        self._m20_strong_up = c.get("mom20_strong_up", 72.0)
        self._m20_moderate_up = c.get("mom20_moderate_up", 62.0)
        self._m20_slight_up = c.get("mom20_slight_up", 55.0)
        self._m20_slight_down = c.get("mom20_slight_down", 42.0)
        self._m20_down = c.get("mom20_down", 25.0)
        self._m20_t = c.get("mom20_thresholds", [30, 15, 5, 0, -10])

        # 60日动量（单调递增：涨幅越大分越高）
        self._m60_extreme_up = c.get("mom60_extreme_up", 88.0)
        self._m60_strong_up = c.get("mom60_strong_up", 75.0)
        self._m60_moderate_up = c.get("mom60_moderate_up", 62.0)
        self._m60_slight_down = c.get("mom60_slight_down", 42.0)
        self._m60_down = c.get("mom60_down", 28.0)
        self._m60_t = c.get("mom60_thresholds", [30, 10, 0, -15])

        # RSI 评分（P1-S3: 放宽超买惩罚，增加趋势判断）
        self._rsi_oversold_bouncing = c.get("rsi_oversold_bouncing", 75.0)
        self._rsi_oversold_falling = c.get("rsi_oversold_falling", 52.0)
        self._rsi_low = c.get("rsi_low", 65.0)
        self._rsi_mid_low = c.get("rsi_mid_low", 58.0)
        self._rsi_neutral = c.get("rsi_neutral", 50.0)
        self._rsi_mid_high = c.get("rsi_mid_high", 45.0)
        self._rsi_high = c.get("rsi_high", 35.0)
        self._rsi_overbought = c.get("rsi_overbought", 35.0)
        self._rsi_overbought_rising = c.get("rsi_overbought_rising", 50.0)
        self._rsi_t = c.get("rsi_thresholds", [25, 35, 45, 55, 65, 75])

    def build_factor_scores(
        self, code: str, stock_data: pd.DataFrame
    ) -> tuple[dict[str, tuple[float, bool]], dict[str, float]]:
        latest = stock_data.iloc[-1]

        short_rev_score, sr_missing = self._score_short_reversal(stock_data)
        multi_mom_score, mm_missing = self._score_multi_momentum(stock_data)
        rsi_score, rsi_missing = self._score_rsi(latest, stock_data)

        factor_scores = {
            "short_reversal": (short_rev_score, sr_missing),
            "multi_momentum": (multi_mom_score, mm_missing),
            "rsi": (rsi_score, rsi_missing),
        }
        weights = {
            "short_reversal": self._w_short_rev,
            "multi_momentum": self._w_multi_mom,
            "rsi": self._w_rsi,
        }
        return factor_scores, weights

    def _score_short_reversal(self, stock_data: pd.DataFrame) -> tuple[float, bool]:
        """短期反转因子：5日涨跌幅评分，结合中期趋势调整极端值"""
        if len(stock_data) < 6:
            return 50.0, True

        pct_col = "pct_chg" if "pct_chg" in stock_data.columns else "close_price"
        if pct_col == "close_price":
            ret_5d = (stock_data["close_price"].iloc[-1] - stock_data["close_price"].iloc[-6]) / stock_data["close_price"].iloc[-6] * 100
        else:
            ret_5d = stock_data["pct_chg"].tail(5).sum()
        if pd.isna(ret_5d):
            return 50.0, True

        # 中期趋势背景：判断是否处于上升趋势中
        latest = stock_data.iloc[-1]
        ma60 = latest.get("ma60", 0)
        close = latest.get("close_price", 0)
        mid_bull = (close > ma60 > 0) if ma60 > 0 else False

        # 趋势调整系数：牛市中放宽对短期超买的惩罚，弱市中保留原始反转逻辑
        base_score = self._sr_extreme_hot
        if ret_5d < self._sr_b_severe:
            base_score = self._sr_severe_oversold
            if mid_bull:
                base_score = 65.0   # 牛市中超跌 → 回调买点，但不过度给分
        elif ret_5d < self._sr_b_oversold:
            base_score = self._sr_oversold
            if mid_bull:
                base_score = 60.0
        elif ret_5d < self._sr_b_clear:
            base_score = self._sr_clear_oversold
            if mid_bull:
                base_score = 56.0
        elif ret_5d < self._sr_b_mild:
            base_score = self._sr_mild_oversold
        elif ret_5d < self._sr_b_neutral:
            base_score = self._sr_slight_fall
        elif ret_5d < self._sr_b_slight_rise:
            base_score = self._sr_slight_rise
        elif ret_5d < self._sr_b_overbought:
            base_score = self._sr_overbought
            if mid_bull:
                base_score = 48.0   # 牛市中温和超买 → 接近中性
        elif ret_5d < self._sr_b_hot:
            base_score = self._sr_hot
            if mid_bull:
                base_score = 42.0   # 牛市中热度偏高 → 中性偏低但不惩罚
        else:
            # ret_5d >= 20%：极度过热
            if mid_bull:
                base_score = 38.0   # 牛市中强涨 → 降低惩罚（原22分）

        return base_score, False

    def _score_multi_momentum(self, stock_data: pd.DataFrame) -> tuple[float, bool]:
        """多周期动量评分（单调递增），内部子周期缺失时权重自动再分配"""
        close = stock_data["close_price"]
        n = len(stock_data)
        latest_close = close.iloc[-1]

        sub_scores: dict[str, float] = {}
        sub_missing: list[str] = []

        # 10日动量（单调递增：涨越多分越高）
        if n >= 10:
            ret_10d = (latest_close - close.iloc[-10]) / close.iloc[-10] * 100
            if ret_10d > self._m10_t[0]:
                sub_scores["mom10"] = self._m10_extreme_up      # ret>15% → 强动量
            elif ret_10d > self._m10_t[1]:
                sub_scores["mom10"] = self._m10_strong_up       # 5%-15%
            elif ret_10d > self._m10_t[2]:
                sub_scores["mom10"] = self._m10_moderate_up     # 0%-5%
            elif ret_10d > self._m10_t[3]:
                sub_scores["mom10"] = self._m10_slight_down     # -5%-0%
            else:
                sub_scores["mom10"] = self._m10_down            # <-5%
        else:
            sub_missing.append("mom10")

        # 20日动量（单调递增：涨越多分越高）
        if n >= 20:
            ret_20d = (latest_close - close.iloc[-20]) / close.iloc[-20] * 100
            if ret_20d > self._m20_t[0]:
                sub_scores["mom20"] = self._m20_extreme_up      # ret>30% → 超强动量
            elif ret_20d > self._m20_t[1]:
                sub_scores["mom20"] = self._m20_strong_up       # 15%-30%
            elif ret_20d > self._m20_t[2]:
                sub_scores["mom20"] = self._m20_moderate_up     # 5%-15%
            elif ret_20d > self._m20_t[3]:
                sub_scores["mom20"] = self._m20_slight_up       # 0%-5%
            elif ret_20d > self._m20_t[4]:
                sub_scores["mom20"] = self._m20_slight_down     # -10%-0%
            else:
                sub_scores["mom20"] = self._m20_down            # <-10%
        else:
            sub_missing.append("mom20")

        # 60日动量（单调递增：涨越多分越高）
        if n >= 60:
            ret_60d = (latest_close - close.iloc[-60]) / close.iloc[-60] * 100
            if ret_60d > self._m60_t[0]:
                sub_scores["mom60"] = self._m60_extreme_up      # ret>30% → 长期强牛
            elif ret_60d > self._m60_t[1]:
                sub_scores["mom60"] = self._m60_strong_up       # 10%-30%
            elif ret_60d > self._m60_t[2]:
                sub_scores["mom60"] = self._m60_moderate_up     # 0%-10%
            elif ret_60d > self._m60_t[3]:
                sub_scores["mom60"] = self._m60_slight_down     # -15%-0%
            else:
                sub_scores["mom60"] = self._m60_down            # <-15%
        else:
            sub_missing.append("mom60")

        # 所有子周期都缺失 → 整个因子缺失
        if not sub_scores:
            return 50.0, True

        # 活跃子周期权重归一化
        sub_weights = {"mom10": self._w_mom10, "mom20": self._w_mom20, "mom60": self._w_mom60}
        active_w = {k: v for k, v in sub_weights.items() if k in sub_scores}
        total_w = sum(active_w.values())

        score = sum(sub_scores[k] * active_w[k] for k in sub_scores) / total_w
        return score, bool(sub_missing)

    def _score_rsi(self, latest: pd.Series, stock_data: pd.DataFrame) -> tuple[float, bool]:
        """RSI评分：高位上升→动量加速(中性)，高位下降→动量衰竭(惩罚)"""
        rsi = latest.get("rsi", np.nan)
        if pd.isna(rsi):
            return 50.0, True

        rsi_rising = False
        if len(stock_data) >= 2 and "rsi" in stock_data.columns:
            prev_rsi = stock_data["rsi"].iloc[-2]
            if not pd.isna(prev_rsi):
                rsi_rising = rsi > prev_rsi

        if rsi < self._rsi_t[0]:
            result = self._rsi_oversold_bouncing if rsi_rising else self._rsi_oversold_falling
        elif rsi < self._rsi_t[1]:
            result = self._rsi_low
        elif rsi < self._rsi_t[2]:
            result = self._rsi_mid_low
        elif rsi < self._rsi_t[3]:
            result = self._rsi_neutral
        elif rsi < self._rsi_t[4]:
            result = self._rsi_mid_high
        elif rsi < self._rsi_t[5]:
            result = self._rsi_high
        else:
            # RSI ≥ 75: 高位仍在上升→动量加速(中性)；高位拐头→动量衰竭(惩罚)
            result = self._rsi_overbought_rising if rsi_rising else self._rsi_overbought
        return result, False


# ==================== 策略C：量价共振策略 ====================

class VolumePriceStrategy(BaseStrategy):
    """
    量价共振策略（权重25%）
    
    专注：量在价先，寻找放量突破/缩量止跌等关键信号
    因子：量比 + 换手率 + 量价相关性 + OBV + 缩量止跌
    """

    def __init__(self):
        super().__init__(strategy_name="VolumePriceStrategy")
        self.logger = get_logger(self.strategy_name)
        self._tech_indicators = TechnicalIndicators()
        self._load_config()

    def _load_config(self):
        c = _get_cfg("volume_price", {})

        # 子因子权重
        self._w_vol_ratio = c.get("vol_ratio_weight", 0.30)
        self._w_turnover = c.get("turnover_weight", 0.15)
        self._w_vp_corr = c.get("vp_corr_weight", 0.20)
        self._w_obv = c.get("obv_weight", 0.20)
        self._w_shrink = c.get("shrink_stop_weight", 0.15)

        # 量比评分
        self._vr_strong = c.get("vol_ratio_strong", 75.0)
        self._vr_moderate = c.get("vol_ratio_moderate", 68.0)
        self._vr_slight = c.get("vol_ratio_slight", 60.0)
        self._vr_normal = c.get("vol_ratio_normal", 50.0)
        self._vr_shrink = c.get("vol_ratio_shrink", 42.0)
        self._vr_extreme_shrink = c.get("vol_ratio_extreme_shrink", 35.0)
        self._vr_t = c.get("vol_ratio_thresholds", [2.5, 1.8, 1.3, 0.8, 0.5])

        # 换手率评分
        self._turn_ideal = c.get("turnover_ideal", 70.0)
        self._turn_good = c.get("turnover_good", 60.0)
        self._turn_high = c.get("turnover_high", 55.0)
        self._turn_low = c.get("turnover_low", 40.0)
        self._turn_extreme = c.get("turnover_extreme", 30.0)
        self._turn_low_bound = c.get("turnover_low_bound", 1.5)
        self._turn_ideal_low = c.get("turnover_ideal_low", 3)
        self._turn_ideal_high = c.get("turnover_ideal_high", 10)
        self._turn_high_bound = c.get("turnover_high_bound", 20)

        # 量价相关性评分
        self._vp_pos_up = c.get("vp_corr_positive_up", 72.0)
        self._vp_pos_down = c.get("vp_corr_positive_down", 40.0)
        self._vp_neg_down = c.get("vp_corr_negative_down", 65.0)
        self._vp_neg_up = c.get("vp_corr_negative_up", 42.0)
        self._vp_neutral = c.get("vp_corr_neutral", 50.0)
        self._vp_pos_bound = c.get("vp_corr_positive_bound", 0.5)
        self._vp_neg_bound = c.get("vp_corr_negative_bound", -0.3)

        # OBV 评分（P2-S6: 多级区分度，基于OBV斜率）
        self._obv_strong_up = c.get("obv_strong_up", 80.0)
        self._obv_up = c.get("obv_up", 60.0)
        self._obv_flat = c.get("obv_flat", 50.0)
        self._obv_down = c.get("obv_down", 35.0)

        # 缩量止跌评分
        self._ss_strong = c.get("shrink_stop_strong", 72.0)
        self._ss_mild = c.get("shrink_stop_mild", 60.0)
        self._ss_vol_only = c.get("shrink_stop_vol_only", 55.0)
        self._ss_none = c.get("shrink_stop_none", 48.0)
        self._ss_price_tight = c.get("shrink_price_range_tight", 2.0)
        self._ss_price_loose = c.get("shrink_price_range_loose", 3.0)
        self._ss_vol_tight = c.get("shrink_vol_ratio_tight", 0.7)
        self._ss_vol_loose = c.get("shrink_vol_ratio_loose", 0.9)
        self._ss_vol_half = c.get("shrink_vol_ratio_half", 0.5)

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """量价策略需要额外计算 turn（换手率近似）"""
        return super().prepare(df, compute_turn=True)

    def build_factor_scores(
        self, code: str, stock_data: pd.DataFrame
    ) -> tuple[dict[str, tuple[float, bool]], dict[str, float]]:
        latest = stock_data.iloc[-1]

        vol_score, vol_missing = self._score_vol_ratio(latest)
        turn_score, turn_missing = self._score_turnover(latest)
        vp_corr_score, vp_missing = self._score_vp_corr(latest, stock_data)
        obv_score, obv_missing = self._score_obv(latest, stock_data)
        shrink_score, shrink_missing = self._score_shrink_stop(stock_data)

        factor_scores = {
            "vol_ratio": (vol_score, vol_missing),
            "turnover": (turn_score, turn_missing),
            "vp_corr": (vp_corr_score, vp_missing),
            "obv": (obv_score, obv_missing),
            "shrink_stop": (shrink_score, shrink_missing),
        }
        weights = {
            "vol_ratio": self._w_vol_ratio,
            "turnover": self._w_turnover,
            "vp_corr": self._w_vp_corr,
            "obv": self._w_obv,
            "shrink_stop": self._w_shrink,
        }
        return factor_scores, weights

    def _score_vol_ratio(self, latest: pd.Series) -> tuple[float, bool]:
        vol_ratio = latest.get("volume_ratio", np.nan)
        if pd.isna(vol_ratio):
            return 50.0, True

        if vol_ratio > self._vr_t[0]:
            return self._vr_strong, False
        elif vol_ratio > self._vr_t[1]:
            return self._vr_moderate, False
        elif vol_ratio > self._vr_t[2]:
            return self._vr_slight, False
        elif vol_ratio > self._vr_t[3]:
            return self._vr_normal, False
        elif vol_ratio > self._vr_t[4]:
            return self._vr_shrink, False
        else:
            return self._vr_extreme_shrink, False

    def _score_turnover(self, latest: pd.Series) -> tuple[float, bool]:
        turn = latest.get("turn", np.nan)
        # 强制转为 float：部分原始数据（如 akShare）的 turn 列可能为字符串类型
        try:
            turn = float(turn)
        except (ValueError, TypeError):
            turn = np.nan
        if pd.isna(turn) or turn <= 0:
            return 50.0, True

        if self._turn_ideal_low <= turn <= self._turn_ideal_high:
            return self._turn_ideal, False
        elif self._turn_low_bound <= turn < self._turn_ideal_low:
            return self._turn_good, False
        elif self._turn_ideal_high < turn <= self._turn_high_bound:
            return self._turn_high, False
        elif turn < self._turn_low_bound:
            return self._turn_low, False
        else:
            return self._turn_extreme, False

    def _score_vp_corr(self, latest: pd.Series, stock_data: pd.DataFrame) -> tuple[float, bool]:
        vp_corr = latest.get("vp_corr", np.nan)
        if pd.isna(vp_corr):
            return 50.0, True

        pct_5d = 0
        if len(stock_data) >= 5 and "pct_chg" in stock_data.columns:
            pct_5d = stock_data["pct_chg"].tail(5).sum()

        if vp_corr > self._vp_pos_bound:
            return (self._vp_pos_up, False) if pct_5d > 0 else (self._vp_pos_down, False)
        elif vp_corr < self._vp_neg_bound:
            return (self._vp_neg_down, False) if pct_5d < 0 else (self._vp_neg_up, False)
        else:
            return self._vp_neutral, False

    def _score_obv(self, latest: pd.Series, stock_data: pd.DataFrame | None = None) -> tuple[float, bool]:
        """OBV评分：基于OBV斜率的多级判断（P2-S6增强区分度）"""
        obv = latest.get("obv", np.nan)
        obv_ma5 = latest.get("obv_ma5", np.nan)
        if pd.isna(obv) or pd.isna(obv_ma5):
            return 50.0, True

        if stock_data is not None and len(stock_data) >= 5 and "obv" in stock_data.columns:
            obv_series = stock_data["obv"].tail(5).dropna()
            if len(obv_series) >= 3:
                # 计算近期OBV斜率（线性回归）
                x = np.arange(len(obv_series))
                slope = np.polyfit(x, obv_series.values, 1)[0]
                # 归一化斜率：除以OBV均值，使不同股价的股票可比
                obv_mean = obv_series.mean()
                if obv_mean > 0:
                    norm_slope = slope / obv_mean * 100
                else:
                    norm_slope = 0
                # 多级判断
                if norm_slope > 1.0:
                    return self._obv_strong_up, False    # OBV加速上升
                elif norm_slope > 0.2:
                    return self._obv_up, False           # OBV上升但减速
                elif norm_slope > -0.2:
                    return self._obv_flat, False         # OBV横盘
                else:
                    return self._obv_down, False         # OBV下降

        # 回退：单日二元判断
        return (self._obv_up if obv > obv_ma5 else self._obv_down), False

    def _score_shrink_stop(self, stock_data: pd.DataFrame) -> tuple[float, bool]:
        if len(stock_data) < 10:
            return 50.0, True

        recent = stock_data.tail(3)
        close = recent["close_price"].values
        volume = recent["volume"].values if "volume" in recent.columns else np.array([])

        if len(close) < 3 or len(volume) < 3:
            return 50.0, True

        price_range = (close.max() - close.min()) / close.mean() * 100 if close.mean() > 0 else 100
        vol_ma5 = stock_data["volume"].tail(6).head(5).mean() if "volume" in stock_data.columns else 0
        vol_latest = volume[-1]

        if price_range < self._ss_price_tight and vol_ma5 > 0 and vol_latest < vol_ma5 * self._ss_vol_tight:
            return self._ss_strong, False
        elif price_range < self._ss_price_loose and vol_ma5 > 0 and vol_latest < vol_ma5 * self._ss_vol_loose:
            return self._ss_mild, False
        elif vol_ma5 > 0 and vol_latest < vol_ma5 * self._ss_vol_half:
            return self._ss_vol_only, False
        else:
            return self._ss_none, False


# ==================== 策略D：低波动质量策略 ====================

class QualityStrategy(BaseStrategy):
    """
    低波动质量策略（权重20%）
    
    专注：防御性配置，适合熊市/震荡市
    因子：历史波动率 + 偏度 + 下行波动率 + 基本面(PE/PB/ROE)
    """

    def __init__(self):
        super().__init__(strategy_name="QualityStrategy")
        self.logger = get_logger(self.strategy_name)
        self._tech_indicators = TechnicalIndicators()
        self._fund_indicators = FundamentalIndicators()
        self._load_config()

    def _load_config(self):
        c = _get_cfg("quality", {})

        # 子因子权重
        self._w_volatility = c.get("volatility_weight", 0.30)
        self._w_skewness = c.get("skewness_weight", 0.20)
        self._w_downside = c.get("downside_weight", 0.20)
        self._w_fundamental = c.get("fundamental_weight", 0.30)

        # 波动率评分
        self._vol_extreme_low = c.get("vol_extreme_low", 78.0)
        self._vol_low = c.get("vol_low", 68.0)
        self._vol_medium = c.get("vol_medium", 55.0)
        self._vol_high = c.get("vol_high", 40.0)
        self._vol_extreme_high = c.get("vol_extreme_high", 25.0)
        self._vol_t = c.get("vol_thresholds", [0.20, 0.30, 0.40, 0.55])

        # 收益偏度评分
        self._sk_strong_pos = c.get("skew_strong_positive", 72.0)
        self._sk_mild_pos = c.get("skew_mild_positive", 63.0)
        self._sk_neutral = c.get("skew_neutral", 50.0)
        self._sk_mild_neg = c.get("skew_mild_negative", 40.0)
        self._sk_strong_neg = c.get("skew_strong_negative", 28.0)
        self._sk_t = c.get("skew_thresholds", [0.8, 0.3, -0.3, -0.8])

        # 下行风险评分
        self._down_extreme_low = c.get("down_extreme_low", 75.0)
        self._down_low = c.get("down_low", 65.0)
        self._down_medium = c.get("down_medium", 52.0)
        self._down_high = c.get("down_high", 38.0)
        self._down_extreme_high = c.get("down_extreme_high", 22.0)
        self._down_t = c.get("down_thresholds", [0.15, 0.25, 0.35, 0.50])

    def build_factor_scores(
        self, code: str, stock_data: pd.DataFrame
    ) -> tuple[dict[str, tuple[float, bool]], dict[str, float]]:
        latest = stock_data.iloc[-1]

        vol_score, vol_missing = self._score_volatility(latest, stock_data)
        skew_score, skew_missing = self._score_skewness(latest)
        down_score, down_missing = self._score_downside(latest)
        fund_score, fund_missing = self._score_fundamental(latest)

        factor_scores = {
            "volatility": (vol_score, vol_missing),
            "skewness": (skew_score, skew_missing),
            "downside": (down_score, down_missing),
            "fundamental": (fund_score, fund_missing),
        }
        weights = {
            "volatility": self._w_volatility,
            "skewness": self._w_skewness,
            "downside": self._w_downside,
            "fundamental": self._w_fundamental,
        }
        return factor_scores, weights

    def _score_volatility(self, latest: pd.Series, stock_data: pd.DataFrame | None = None) -> tuple[float, bool]:
        """波动率评分：区分上行/下行波动，上涨波动不惩罚"""
        hist_vol = latest.get("hist_vol", np.nan)
        if pd.isna(hist_vol):
            return 50.0, True

        # 基础分：按历史波动率分档
        if hist_vol < self._vol_t[0]:
            base = self._vol_extreme_low
        elif hist_vol < self._vol_t[1]:
            base = self._vol_low
        elif hist_vol < self._vol_t[2]:
            base = self._vol_medium
        elif hist_vol < self._vol_t[3]:
            base = self._vol_high
        else:
            base = self._vol_extreme_high

        # P1-S5: 方向性调整 — 上行波动为主导的股票不应被惩罚
        if stock_data is not None and len(stock_data) >= 10 and "pct_chg" in stock_data.columns:
            recent = stock_data.tail(20)
            ret = recent["pct_chg"]
            up_ret = ret.where(ret > 0, 0)
            down_ret = ret.where(ret < 0, 0)
            up_std = up_ret[up_ret > 0].std() if (up_ret > 0).sum() >= 3 else 0
            down_std = abs(down_ret[down_ret < 0].std()) if (down_ret < 0).sum() >= 3 else 0
            if down_std > 0 and up_std > 0:
                ratio = up_std / down_std
                if ratio > 1.5:
                    base = min(100, base + 10)      # 上行波动主导 → 加分
                elif ratio < 0.67:
                    base = max(10, base - 5)         # 下行波动主导 → 减分

        return base, False

    def _score_skewness(self, latest: pd.Series) -> tuple[float, bool]:
        skew = latest.get("ret_skew", np.nan)
        if pd.isna(skew):
            return 50.0, True

        if skew > self._sk_t[0]:
            return self._sk_strong_pos, False
        elif skew > self._sk_t[1]:
            return self._sk_mild_pos, False
        elif skew > self._sk_t[2]:
            return self._sk_neutral, False
        elif skew > self._sk_t[3]:
            return self._sk_mild_neg, False
        else:
            return self._sk_strong_neg, False

    def _score_downside(self, latest: pd.Series) -> tuple[float, bool]:
        down_vol = latest.get("down_vol", np.nan)
        if pd.isna(down_vol):
            return 50.0, True

        if down_vol < self._down_t[0]:
            return self._down_extreme_low, False
        elif down_vol < self._down_t[1]:
            return self._down_low, False
        elif down_vol < self._down_t[2]:
            return self._down_medium, False
        elif down_vol < self._down_t[3]:
            return self._down_high, False
        else:
            return self._down_extreme_high, False

    def _get_fund_value(self, latest: pd.Series, *names: str) -> float | None:
        """按候选列名依次取值（对齐裸列名与 fundamental_* 前缀），无效返回 None。"""
        for name in names:
            v = latest.get(name, None)
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
        return None

    def _score_fundamental(self, latest: pd.Series) -> tuple[float, bool]:
        # 列名对齐：优先裸列名（daily_basic 合并路径），回退 fundamental_* 前缀（手动注入路径）
        pe_val = self._get_fund_value(latest, "pe_ttm", "fundamental_pe_ttm")
        pb_val = self._get_fund_value(latest, "pb", "fundamental_pb")
        roe_val = self._get_fund_value(latest, "roe", "fundamental_roe")
        debt_val = self._get_fund_value(latest, "debt_to_equity", "fundamental_debt_to_equity")

        # 所有基本面指标均缺失 → 标记该因子缺失，由缺失再分配逻辑降级处理
        all_missing = (pe_val is None and pb_val is None and roe_val is None and debt_val is None)

        score = self._fund_indicators.score_fundamental(
            pe=pe_val, pb=pb_val, roe=roe_val, debt_to_equity=debt_val,
        )
        return score, all_missing
