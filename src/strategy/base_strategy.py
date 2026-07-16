from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger
from src.indicators.technical_indicators import TechnicalIndicators


# ==================== 缺失数据处理（共享） ====================

def _get_missing_mode() -> str:
    """读取缺失数据处理模式"""
    return config_loader.get("strategy.missing_data.mode", "redistribute")


def _redistribute_scores(
    factor_scores: dict[str, tuple[float, bool]],
    factor_weights: dict[str, float],
    strategy_name: str = "",
    code: str = "",
) -> tuple[float, list[str], str]:
    """
    根据缺失因子重新分配权重并计算得分。

    Args:
        factor_scores: {因子名: (得分, 是否缺失)}
        factor_weights: {因子名: 原始权重}

    Returns:
        (最终得分, 缺失因子列表, 完整度标签: full/partial/insufficient)
    """
    mode = _get_missing_mode()
    missing = [name for name, (_, m) in factor_scores.items() if m]

    if mode == "neutral":
        # 中性模式：缺失因子当50分，按原权重计入
        total_w = sum(factor_weights.values())
        score = sum(
            factor_scores[name][0] * factor_weights[name]
            for name in factor_scores
        ) / total_w if total_w > 0 else 50.0
        completeness = "full" if not missing else "partial"
        return score, missing, completeness

    if mode == "penalize":
        # 惩罚模式：缺失因子给30分（低于中性50），按原权重计入
        total_w = sum(factor_weights.values())
        score = 0.0
        for name in factor_scores:
            s, m = factor_scores[name]
            score += (30.0 if m else s) * factor_weights[name]
        score = score / total_w if total_w > 0 else 50.0
        completeness = "full" if not missing else "partial"
        return score, missing, completeness

    if mode == "exclude":
        # 排除模式：任何因子缺失 → 该策略直接标记 incomplete
        if missing:
            return 50.0, missing, "insufficient"
        total_w = sum(factor_weights.values())
        score = sum(
            factor_scores[name][0] * factor_weights[name]
            for name in factor_scores
        ) / total_w if total_w > 0 else 50.0
        return score, missing, "full"

    # 默认 redistribute：缺失因子排除，剩余权重归一化
    active_weights = {name: w for name, w in factor_weights.items() if name not in missing}
    if not active_weights:
        return 50.0, missing, "insufficient"

    total_w = sum(active_weights.values())
    score = sum(
        factor_scores[name][0] * active_weights[name]
        for name in active_weights
    ) / total_w

    completeness = "full" if not missing else "partial"
    return score, missing, completeness


@dataclass
class Position:
    code: str
    shares: float
    cost_price: float
    current_price: float
    buy_date: datetime
    holding_days: int = 0
    buy_score: float = 50.0          # 买入时的综合得分
    highest_price: float = 0.0       # 持仓期间达到的最高价（用于移动止盈）
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def profit_loss(self) -> float:
        return (self.current_price - self.cost_price) / self.cost_price * 100
    
    @property
    def drawdown_from_peak(self) -> float:
        """从持仓期最高点回撤的比例（%），最高价未设置时返回 0"""
        if self.highest_price <= 0:
            return 0.0
        return (self.current_price - self.highest_price) / self.highest_price * 100


@dataclass
class StrategyContext:
    date: datetime
    available_cash: float
    positions: dict[str, Position]
    total_assets: float
    
    @property
    def position_value(self) -> float:
        return sum(pos.market_value for pos in self.positions.values())


class BaseStrategy(ABC):
    
    def __init__(self, strategy_name: str | None = None):
        config = config_loader.get("strategy", {}).get("default", {})
        selection_config = config_loader.get("strategy", {}).get("selection", {})
        sell_cfg = config_loader.get("strategy", {}).get("sell_signals", {})
        
        self.strategy_name = strategy_name or self.__class__.__name__
        self.logger = get_logger(self.strategy_name)
        
        # 原有止损止盈（保留兼容，新逻辑中 stop_loss_pct 被 hard_stop_loss_pct 替代）
        self.stop_loss_pct = sell_cfg.get("hard_stop_loss_pct", config.get("stop_loss_pct", -12.0))
        self.take_profit_pct = sell_cfg.get("take_profit_backstop_pct", config.get("take_profit_pct", 80.0))
        self.max_position_pct = config.get("max_position_pct", 30.0)
        self.max_positions = config.get("max_positions", 10)
        self.min_score_threshold = selection_config.get("min_score_threshold", 50.0)
        
        # 交易频率控制
        self.cooldown_days = selection_config.get("cooldown_days", 5)
        self.max_trades_per_day = selection_config.get("max_trades_per_day", 5)
        self.max_buy_per_day = selection_config.get("max_buy_per_day", 2)
        self.max_sell_per_day = selection_config.get("max_sell_per_day", 5)
        
        # ===== 卖出信号配置 =====
        # 最短持有期（除硬止损外）
        self._min_holding_days = sell_cfg.get("min_holding_days", 10)
        # 移动止盈
        self._trailing_stop_drawdown = sell_cfg.get("trailing_stop_drawdown", -15.0)
        self._trailing_stop_drawdown_core = sell_cfg.get("trailing_stop_drawdown_core", -20.0)
        self._trailing_stop_min_profit = sell_cfg.get("trailing_stop_min_profit", 10.0)
        self._core_position_count = sell_cfg.get("core_position_count", 3)
        # 时间止损
        self._time_stop_days = sell_cfg.get("time_stop_days", 60)
        self._time_stop_loss_pct = sell_cfg.get("time_stop_loss_pct", -5.0)
        # MA 趋势结构
        self._ma_dead_cross_days = sell_cfg.get("ma_dead_cross_days", 3)
        self._ma20_decline_lookback = sell_cfg.get("ma20_decline_lookback", 5)
        # ADX 趋势衰竭
        self._adx_exhaustion_threshold = sell_cfg.get("adx_exhaustion_threshold", 18.0)
        self._adx_decline_days = sell_cfg.get("adx_decline_days", 5)
        self._adx_decline_from_threshold = sell_cfg.get("adx_decline_from_threshold", 30.0)
        # 得分恶化
        self._score_drop_ratio = sell_cfg.get("score_drop_ratio", 0.55)
        self._score_below_threshold = sell_cfg.get("score_below_threshold", 50.0)
        self._score_decline_days = sell_cfg.get("score_decline_days", 5)
        self._score_decline_cumulative = sell_cfg.get("score_decline_cumulative", 20.0)
        # 动量衰竭
        self._mom_neg_count = sell_cfg.get("mom_neg_count", 2)
        self._rsi_overbought_high = sell_cfg.get("rsi_overbought_high", 70.0)
        self._rsi_overbought_exit = sell_cfg.get("rsi_overbought_exit", 65.0)
        self._rsi_core_relax = sell_cfg.get("rsi_core_relax", 10.0)
        self._short_crash_pct = sell_cfg.get("short_crash_pct", -12.0)
        # 量价背离
        self._vol_diverge_price_pct = sell_cfg.get("vol_diverge_price_pct", 5.0)
        self._vol_diverge_vol_ratio = sell_cfg.get("vol_diverge_vol_ratio", 0.6)
        self._vol_diverge_severe_vol_ratio = sell_cfg.get("vol_diverge_severe_vol_ratio", 0.4)
        self._vol_diverge_severe_price_pct = sell_cfg.get("vol_diverge_severe_price_pct", 8.0)
        self._obv_divergence_lookback = sell_cfg.get("obv_divergence_lookback", 20)
        self._crash_vol_ratio = sell_cfg.get("crash_vol_ratio", 2.0)
        self._crash_price_pct = sell_cfg.get("crash_price_pct", -5.0)
        # 冷却期（按卖出原因区分）
        self._cooldown_map: dict[str, int] = {
            "stop_loss": sell_cfg.get("cooldown_stop_loss", 10),
            "trend_deterioration": sell_cfg.get("cooldown_trend_deterioration", 20),
            "score_drop": sell_cfg.get("cooldown_score_drop", 20),
            "trailing_stop": sell_cfg.get("cooldown_trailing_stop", 15),
            "volume_price": sell_cfg.get("cooldown_volume_price", 15),
            "momentum": sell_cfg.get("cooldown_momentum", 15),
            "time_stop": sell_cfg.get("cooldown_time_stop", 20),
            "take_profit": sell_cfg.get("cooldown_take_profit", 15),
            "default": sell_cfg.get("cooldown_default", 15),
        }
        self._last_sell_reason: str = ""  # 最近一次卖出的原因（供 backtest 引擎读取）
        
        # 记录每只股票的最后卖出日期（用于冷却期）-> (date, reason)
        self._last_sell_dates: dict[str, tuple[datetime, str]] = {}
        
        # 记录每天的买卖次数（买卖分开限制）
        self._daily_buy_counts: dict[str, int] = {}
        self._daily_sell_counts: dict[str, int] = {}
        
        self._prepared_data: pd.DataFrame | None = None

        # 分数完整度追踪（供 get_score_completeness 使用）
        self._last_completeness: str = "unknown"
        self._last_missing_factors: list[str] = []
    
    def prepare(self, df: pd.DataFrame, compute_turn: bool = False) -> pd.DataFrame:
        """
        统一准备数据：按 code 分组计算全量技术指标，避免多股票拼接时跨边界污染。

        Args:
            df: 含 close_price/volume 等列的行情 DataFrame（可含多只股票）
            compute_turn: 是否额外计算 turn（换手率近似），量价策略需要
        """
        tech = getattr(self, "_tech_indicators", None) or TechnicalIndicators()
        df = df.copy()

        if "code" in df.columns and df["code"].nunique() > 1:
            result_frames = []
            for _code, group in df.groupby("code", sort=False):
                group = group.copy()
                group["pct_chg"] = group["close_price"].pct_change() * 100
                group = tech.add_all_indicators(group)
                if compute_turn and "volume" in group.columns:
                    if "turn" in group.columns:
                        try:
                            group["turn"] = pd.to_numeric(group["turn"], errors="coerce")
                        except Exception:
                            group["turn"] = np.nan
                        avg_vol = group["volume"].rolling(window=20, min_periods=1).mean()
                        mask = group["turn"].isna()
                        group.loc[mask, "turn"] = (group.loc[mask, "volume"] / avg_vol.loc[mask].replace(0, np.nan)) * 100
                    else:
                        avg_vol = group["volume"].rolling(window=20, min_periods=1).mean()
                        group["turn"] = (group["volume"] / avg_vol.replace(0, np.nan)) * 100
                result_frames.append(group)
            return pd.concat(result_frames, ignore_index=True)

        df["pct_chg"] = df["close_price"].pct_change() * 100
        df = tech.add_all_indicators(df)
        if compute_turn and "volume" in df.columns:
            # 若已有 turn 列但为非数值型（如部分 akShare 数据为字符串），重新计算
            if "turn" in df.columns:
                try:
                    df["turn"] = pd.to_numeric(df["turn"], errors="coerce")
                except Exception:
                    df["turn"] = np.nan
                # 补全 NaN 值：用 20日均量 反推换手率
                avg_vol = df["volume"].rolling(window=20, min_periods=1).mean()
                mask = df["turn"].isna()
                df.loc[mask, "turn"] = (df.loc[mask, "volume"] / avg_vol.loc[mask].replace(0, np.nan)) * 100
            else:
                avg_vol = df["volume"].rolling(window=20, min_periods=1).mean()
                df["turn"] = (df["volume"] / avg_vol.replace(0, np.nan)) * 100
        return df

    def score_stock(self, code: str, stock_data: pd.DataFrame) -> float:
        """
        通用子策略评分模板：空数据/价格校验 → 各因子评分 → 缺失再分配。

        子类只需实现 :meth:`build_factor_scores` 返回 (因子分数字典, 权重字典)。
        """
        self._last_missing_factors = []
        self._last_completeness = "unknown"

        if stock_data.empty:
            self._last_completeness = "insufficient"
            self._last_missing_factors = ["all"]
            return 50.0

        latest = stock_data.iloc[-1]
        close_price = latest.get("close_price", 0)
        if pd.isna(close_price) or close_price <= 0:
            self._last_completeness = "insufficient"
            self._last_missing_factors = ["price"]
            return 50.0

        factor_scores, weights = self.build_factor_scores(code, stock_data)
        return self.finalize_score(factor_scores, weights, code)

    def build_factor_scores(
        self, code: str, stock_data: pd.DataFrame
    ) -> tuple[dict[str, tuple[float, bool]], dict[str, float]]:
        """
        子类实现：返回 (因子分数字典 {名: (分, 是否缺失)}, 权重字典 {名: 权重})。

        若子类完全自定义 score_stock（如 SelectionStrategy），可不实现本方法。
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} 必须实现 build_factor_scores 或重写 score_stock"
        )

    def finalize_score(
        self,
        factor_scores: dict[str, tuple[float, bool]],
        weights: dict[str, float],
        code: str,
    ) -> float:
        """统一处理缺失再分配 + 完整度记录 + debug 日志，返回最终得分。"""
        score, missing, completeness = _redistribute_scores(
            factor_scores, weights, self.strategy_name, code
        )
        self._last_missing_factors = missing
        self._last_completeness = completeness

        if missing:
            self.logger.debug(
                f"{self.strategy_name} factors missing for {code}",
                missing_factors=missing,
                completeness=completeness,
            )
        return score

    def get_score_completeness(self) -> dict:
        return {
            "completeness": getattr(self, "_last_completeness", "unknown"),
            "missing_factors": getattr(self, "_last_missing_factors", []),
        }

    def filter_stock(self, daily_data: pd.Series, df: pd.DataFrame) -> bool:
        """默认筛选：不做过滤（子类 SelectionStrategy 会重写为价格/市值/涨跌停/ST 过滤）"""
        return True

    def should_buy(self, code: str, daily_data: pd.Series, ctx: StrategyContext, precomputed_score: float | None = None) -> bool:
        self._validate_no_future_data(daily_data)
        
        if ctx.available_cash <= 0:
            self.logger.debug("Insufficient cash", code=code)
            return False
        
        if len(ctx.positions) >= self.max_positions:
            self.logger.debug("Max positions reached", code=code, max_positions=self.max_positions)
            return False
        
        if code in ctx.positions:
            self.logger.debug("Already holding position", code=code)
            return False
        
        # 检查冷却期（按卖出原因使用不同冷却天数）
        if code in self._last_sell_dates:
            last_sell_date, sell_reason = self._last_sell_dates[code]
            cooldown = self._cooldown_map.get(sell_reason, self._cooldown_map["default"])
            days_since_sell = (ctx.date - last_sell_date).days
            if days_since_sell < cooldown:
                self.logger.debug(
                    "In cooldown period",
                    code=code,
                    days_since_sell=days_since_sell,
                    cooldown_days=cooldown,
                    sell_reason=sell_reason,
                )
                return False
        
        # 检查买入频率限制
        date_str = ctx.date.strftime("%Y-%m-%d")
        if date_str in self._daily_buy_counts:
            if self._daily_buy_counts[date_str] >= self.max_buy_per_day:
                self.logger.debug(
                    "Max buy per day reached",
                    date=date_str,
                    buys=self._daily_buy_counts[date_str],
                    max_buys=self.max_buy_per_day,
                )
                return False
        
        # 使用预计算的得分，避免重复调用 score_stock()
        if precomputed_score is not None:
            score = precomputed_score
        elif self._prepared_data is not None:
            code_data = self._prepared_data[self._prepared_data["code"] == code]
            score = self.score_stock(code, code_data)
        else:
            score = 50.0
        
        if score < self.min_score_threshold:
            self.logger.debug(
                "Score below threshold",
                code=code,
                score=score,
                threshold=self.min_score_threshold,
            )
            return False
        
        position_value = daily_data.get("close_price", 0) * 100
        position_pct = position_value / ctx.total_assets * 100
        
        if position_pct > self.max_position_pct:
            self.logger.debug(
                "Position size exceeds limit",
                code=code,
                position_pct=position_pct,
                max_position_pct=self.max_position_pct,
            )
            return False
        
        self.logger.info(
            "Buy signal triggered",
            code=code,
            score=score,
            price=daily_data.get("close_price"),
        )
        
        return True
    
    def should_sell(self, code: str, daily_data: pd.Series, position: Position, ctx: StrategyContext) -> tuple[bool, str]:
        """
        五维趋势恶化卖出逻辑（返回 (是否卖出, 卖出原因)）。
        
        优先级从高到低：
        1. 硬止损（无条件）
        2. 趋势结构破坏（MA死叉/ADX衰竭）
        3. 得分显著恶化
        4. 极端量价背离（可单独触发）
        5. 动量衰竭 + 量价背离（联合触发）
        6. 移动止盈（回撤保护）
        7. 时间止损
        8. 保底固定止盈
        
        核心仓位（浮盈 Top-N）在移动止盈和 RSI 阈值上享受更大容忍度。
        """
        self._validate_no_future_data(daily_data)
        self._last_sell_reason = ""
        
        if code not in ctx.positions:
            return False, ""
        
        current_price = daily_data.get("close_price", position.current_price)
        profit_loss = (current_price - position.cost_price) / position.cost_price * 100
        
        # 更新持仓期间最高价
        if current_price > position.highest_price:
            position.highest_price = current_price
        
        # 判断是否为核心仓位（浮盈最高的前 N 只）
        is_core = self._is_core_position(code, ctx)
        
        # ---- 维度5-1：硬止损（最高优先级，无条件卖出）----
        if profit_loss <= self.stop_loss_pct:
            self._last_sell_reason = "stop_loss"
            self.logger.warning("Stop loss triggered", code=code,
                              profit_loss=round(profit_loss, 2), stop_loss=self.stop_loss_pct)
            return True, "stop_loss"
        
        # ---- 最短持有期检查（除硬止损外，持有不足 min_holding_days 不触发其他卖出信号）----
        if position.holding_days < self._min_holding_days:
            return False, ""
        
        # ---- 获取股票历史数据（用于趋势检测）----
        stock_data = None
        if self._prepared_data is not None:
            stock_data = self._prepared_data[self._prepared_data["code"] == code]
        
        # ---- 维度5-8：保底固定止盈（最后检查，用于超大行情的兜底保护）----
        if profit_loss >= self.take_profit_pct:
            self._last_sell_reason = "take_profit"
            self.logger.info("Take profit backstop triggered", code=code,
                           profit_loss=round(profit_loss, 2), threshold=self.take_profit_pct)
            return True, "take_profit"
        
        # ---- 维度1：趋势结构破坏 ----
        if stock_data is not None and not stock_data.empty:
            if self._check_trend_breakdown(daily_data, stock_data, is_core):
                self._last_sell_reason = "trend_deterioration"
                return True, "trend_deterioration"
        
        # ---- 维度2：得分显著恶化 ----
        if stock_data is not None and not stock_data.empty:
            if self._check_score_deterioration(code, stock_data, position):
                self._last_sell_reason = "score_drop"
                return True, "score_drop"
        
        # ---- 维度4：极端量价背离（可单独触发）----
        if stock_data is not None and not stock_data.empty:
            if self._check_severe_volume_price_divergence(daily_data, stock_data):
                self._last_sell_reason = "volume_price"
                return True, "volume_price"
        
        # ---- 维度3+4联合：动量衰竭 + 量价背离 ----
        momentum_exhausted = False
        vp_diverged = False
        if stock_data is not None and not stock_data.empty:
            momentum_exhausted = self._check_momentum_exhaustion(daily_data, stock_data, position, is_core)
            vp_diverged = self._check_volume_price_divergence(daily_data, stock_data)
            if momentum_exhausted and vp_diverged:
                self._last_sell_reason = "momentum"
                return True, "momentum"
        
        # ---- 维度5-3：移动止盈（从最高点回撤保护）----
        drawdown = position.drawdown_from_peak
        trailing_threshold = self._trailing_stop_drawdown_core if is_core else self._trailing_stop_drawdown
        if drawdown <= trailing_threshold and position.profit_loss >= self._trailing_stop_min_profit:
            self._last_sell_reason = "trailing_stop"
            self.logger.info("Trailing stop triggered", code=code,
                           profit_loss=round(position.profit_loss, 2),
                           drawdown=round(drawdown, 2), threshold=trailing_threshold,
                           is_core=is_core)
            return True, "trailing_stop"
        
        # ---- 维度5-5：时间止损（长时间不涨的股票）----
        if position.holding_days >= self._time_stop_days and profit_loss <= self._time_stop_loss_pct:
            self._last_sell_reason = "time_stop"
            self.logger.info("Time stop triggered", code=code,
                           holding_days=position.holding_days, profit_loss=round(profit_loss, 2))
            return True, "time_stop"
        
        # ---- 所有检查通过，继续持有 ----
        return False, ""
    
    def _is_core_position(self, code: str, ctx: StrategyContext) -> bool:
        """判断当前持仓是否为核心仓位（浮盈最高的前 N 只）"""
        if not ctx.positions or self._core_position_count <= 0:
            return False
        sorted_positions = sorted(
            ctx.positions.values(),
            key=lambda p: p.profit_loss,
            reverse=True,
        )
        core_codes = {p.code for p in sorted_positions[:self._core_position_count]}
        return code in core_codes
    
    # ==================== 趋势恶化检测子方法 ====================
    
    def _check_trend_breakdown(self, daily_data: pd.Series, stock_data: pd.DataFrame,
                               is_core: bool) -> bool:
        """维度1：检测趋势结构是否被破坏（MA死叉 / MA20拐头 / ADX衰竭）"""
        close = daily_data.get("close_price", 0)
        ma20 = daily_data.get("ma20", 0)
        ma60 = daily_data.get("ma60", 0)
        
        # 1) MA中期死叉：price < MA20 < MA60，连续确认 N 天
        if close > 0 and ma20 > 0 and ma60 > 0:
            if close < ma20 < ma60:
                if self._confirm_continuous(stock_data, "ma_dead_cross", self._ma_dead_cross_days):
                    self.logger.info("MA dead cross (mid-term trend broken)", code=daily_data.get("code"),
                                   close=round(close, 2), ma20=round(ma20, 2), ma60=round(ma60, 2))
                    return True
        
        # 2) MA20 拐头下行（需幅度确认，下降超过 ma20_decline_pct 才触发）
        if self._ma20_decline_lookback > 0 and len(stock_data) >= self._ma20_decline_lookback:
            prev_ma20 = stock_data["ma20"].iloc[-self._ma20_decline_lookback] if "ma20" in stock_data.columns else 0
            if ma20 > 0 and prev_ma20 > 0 and ma20 < prev_ma20 * (1 - self._ma20_decline_pct) and close < ma20:
                self.logger.info("MA20 declining (trend turning)", code=daily_data.get("code"),
                               ma20_now=round(ma20, 2), ma20_prev=round(prev_ma20, 2),
                               decline_pct=round((prev_ma20 - ma20) / prev_ma20 * 100, 2))
                return True
        
        # 3) ADX 趋势衰竭
        adx = daily_data.get("adx", 0)
        pdi = daily_data.get("pdi", 0)
        mdi = daily_data.get("mdi", 0)
        if adx > 0 and adx < self._adx_exhaustion_threshold and pdi < mdi:
            self.logger.info("ADX trend exhaustion", code=daily_data.get("code"), adx=round(adx, 2))
            return True
        
        # 4) ADX 从高位持续下降
        if adx > 0 and "adx" in stock_data.columns and len(stock_data) >= self._adx_decline_days:
            adx_series = stock_data["adx"].tail(self._adx_decline_days)
            adx_start = adx_series.iloc[0] if len(adx_series) > 0 else 0
            adx_end = adx_series.iloc[-1] if len(adx_series) > 0 else 0
            if (adx_start > self._adx_decline_from_threshold and
                adx_end < adx_start and
                all(adx_series.diff().dropna() <= 0)):
                self.logger.info("ADX declining from high level", code=daily_data.get("code"),
                               adx_start=round(adx_start, 2), adx_end=round(adx_end, 2))
                return True
        
        return False
    
    def _check_score_deterioration(self, code: str, stock_data: pd.DataFrame,
                                   position: Position) -> bool:
        """维度2：检测得分是否显著恶化"""
        current_score = self.score_stock(code, stock_data)
        
        # 1) 得分断崖下降（相对买入时）
        if position.buy_score > 0:
            if current_score < position.buy_score * self._score_drop_ratio:
                self.logger.info("Score dropped significantly", code=code,
                               buy_score=round(position.buy_score, 1),
                               current_score=round(current_score, 1))
                return True
        
        # 2) 得分跌破绝对阈值
        if current_score < self._score_below_threshold:
            # 连续 N 天确认
            if self._confirm_continuous(stock_data, "score_below", self._score_decline_days):
                self.logger.info("Score below threshold persistently", code=code,
                               current_score=round(current_score, 1),
                               threshold=self._score_below_threshold)
                return True
        
        return False
    
    def _check_momentum_exhaustion(self, daily_data: pd.Series, stock_data: pd.DataFrame,
                                   position: Position, is_core: bool) -> bool:
        """维度3：检测动量是否衰竭"""
        close = daily_data.get("close_price", 0)
        n = len(stock_data)
        
        # 1) 多周期动量转负
        neg_count = 0
        if n >= 20:
            ret_20d = (close - stock_data["close_price"].iloc[-20]) / stock_data["close_price"].iloc[-20] * 100
            if ret_20d < 0:
                neg_count += 1
        if n >= 60:
            ret_60d = (close - stock_data["close_price"].iloc[-60]) / stock_data["close_price"].iloc[-60] * 100
            if ret_60d < 0:
                neg_count += 1
        if neg_count >= self._mom_neg_count:
            return True
        
        # 2) RSI 高位死亡交叉（核心仓位放宽阈值）
        rsi = daily_data.get("rsi", 50)
        rsi_exit = self._rsi_overbought_exit - (self._rsi_core_relax if is_core else 0)
        if rsi > self._rsi_overbought_high and "rsi" in stock_data.columns and len(stock_data) >= 2:
            prev_rsi = stock_data["rsi"].iloc[-2]
            if not pd.isna(prev_rsi) and rsi < prev_rsi:
                # RSI 从高位回落
                macd = daily_data.get("macd", 0)
                macd_signal = daily_data.get("macd_signal", 0)
                if macd < macd_signal:
                    return True
        
        # 3) 短期暴跌（5日跌幅超阈值 + 跌破MA20）
        if len(stock_data) >= 5 and "pct_chg" in stock_data.columns:
            ret_5d = stock_data["pct_chg"].tail(5).sum()
            ma20 = daily_data.get("ma20", 0)
            if ret_5d <= self._short_crash_pct and close < ma20:
                return True
        
        return False
    
    def _check_volume_price_divergence(self, daily_data: pd.Series, stock_data: pd.DataFrame) -> bool:
        """维度4（普通）：检测量价背离（需与其他维度联合触发）"""
        # 1) 缩量上涨
        if len(stock_data) >= 5 and "volume" in stock_data.columns and "close_price" in stock_data.columns:
            close_recent = stock_data["close_price"].tail(5)
            vol_recent = stock_data["volume"].tail(5)
            price_chg_5d = (close_recent.iloc[-1] - close_recent.iloc[0]) / close_recent.iloc[0] * 100
            vol_ma20 = stock_data["volume"].tail(20).mean() if len(stock_data) >= 20 else vol_recent.mean()
            vol_avg_5d = vol_recent.mean()
            if price_chg_5d > self._vol_diverge_price_pct and vol_ma20 > 0 and vol_avg_5d < vol_ma20 * self._vol_diverge_vol_ratio:
                return True
        
        # 2) OBV 顶背离
        if "obv" in stock_data.columns and len(stock_data) >= self._obv_divergence_lookback:
            obv_now = daily_data.get("obv", 0)
            obv_past = stock_data["obv"].iloc[-self._obv_divergence_lookback] if len(stock_data) >= self._obv_divergence_lookback else obv_now
            close_now = daily_data.get("close_price", 0)
            close_past = stock_data["close_price"].iloc[-self._obv_divergence_lookback]
            if close_now > close_past and obv_now < obv_past and obv_past > 0:
                return True
        
        return False
    
    def _check_severe_volume_price_divergence(self, daily_data: pd.Series, stock_data: pd.DataFrame) -> bool:
        """维度4（极端）：极端量价背离可单独触发卖出"""
        # 1) 极端缩量上涨
        if len(stock_data) >= 5 and "volume" in stock_data.columns and "close_price" in stock_data.columns:
            close_recent = stock_data["close_price"].tail(5)
            vol_recent = stock_data["volume"].tail(5)
            price_chg_5d = (close_recent.iloc[-1] - close_recent.iloc[0]) / close_recent.iloc[0] * 100
            vol_ma20 = stock_data["volume"].tail(20).mean() if len(stock_data) >= 20 else vol_recent.mean()
            vol_avg_5d = vol_recent.mean()
            if (price_chg_5d > self._vol_diverge_severe_price_pct and
                vol_ma20 > 0 and vol_avg_5d < vol_ma20 * self._vol_diverge_severe_vol_ratio):
                self.logger.info("Severe volume-price divergence (shrinking volume + rising price)",
                               code=daily_data.get("code"))
                return True
        
        # 2) 放量暴跌
        vol_ratio = daily_data.get("volume_ratio", 1.0)
        pct_chg = daily_data.get("pct_chg", 0)
        if vol_ratio > self._crash_vol_ratio and pct_chg <= self._crash_price_pct:
            self.logger.info("High volume crash", code=daily_data.get("code"),
                           vol_ratio=round(vol_ratio, 2), pct_chg=round(pct_chg, 2))
            return True
        
        return False
    
    def _confirm_continuous(self, stock_data: pd.DataFrame, signal_type: str,
                            required_days: int) -> bool:
        """
        确认某个信号是否连续出现了 required_days 天。
        用于避免单日噪声误判。
        """
        if len(stock_data) < required_days:
            return False
        
        recent = stock_data.tail(required_days)
        
        if signal_type == "ma_dead_cross":
            for i in range(len(recent)):
                row = recent.iloc[i]
                close = row.get("close_price", 0)
                ma20 = row.get("ma20", 0)
                ma60 = row.get("ma60", 0)
                if not (close > 0 and ma20 > 0 and ma60 > 0 and close < ma20 < ma60):
                    return False
            return True
        
        if signal_type == "score_below":
            # 需要外部传入评分，这里依赖 _prepared_data
            return True  # 简化为单日判断，由 _check_score_deterioration 处理
        
        return True
    
    def _check_sell_signal(
        self,
        code: str,
        daily_data: pd.Series,
        position: Position,
        ctx: StrategyContext,
    ) -> tuple[bool, str]:
        """子类可重写此方法添加自定义卖出信号（保留为扩展点，新逻辑已集成在 should_sell 中）"""
        return False, ""
    
    def execute(self, df: pd.DataFrame, ctx: StrategyContext, current_date: datetime | None = None) -> dict[str, Any]:
        self.logger.info(
            "Executing strategy",
            strategy=self.strategy_name,
            date=str(ctx.date),
            positions=len(ctx.positions),
        )
        
        prepared_df = self.prepare(df)
        
        if prepared_df.empty:
            self.logger.warning("No data after preparation")
            return {"buy_signals": [], "sell_signals": [], "scores": {}}
        
        self._prepared_data = prepared_df
        
        scores = {}
        buy_signals: list[tuple[str, float]] = []
        sell_signals: list[tuple[str, str]] = []  # (code, sell_reason)
        
        # 如果指定了当前交易日，则只处理当前交易日的数据
        if current_date is not None:
            # 筛选出当前交易日的股票代码
            current_date_df = prepared_df[prepared_df["date"] == current_date]
            current_codes = current_date_df["code"].unique()
            
            for code in current_codes:
                # 获取该股票的历史数据（用于计算动态评分）
                code_data = prepared_df[prepared_df["code"] == code]
                
                if code_data.empty:
                    continue
                
                # 获取最新一天的数据
                latest_data = code_data.iloc[-1]
                
                # 硬筛选：与选股模块保持一致（仅对未持仓股票做筛选，已持仓的允许继续持有）
                if code not in ctx.positions:
                    if not self.filter_stock(latest_data, code_data):
                        continue
                
                # 计算评分（传入整个DataFrame，而不是只传入最新一天的数据）
                score = self.score_stock(code, code_data)
                scores[code] = score
                
                if code in ctx.positions:
                    position = ctx.positions[code]
                    should_sell_flag, sell_reason = self.should_sell(code, latest_data, position, ctx)
                    if should_sell_flag:
                        sell_signals.append((code, sell_reason))
                else:
                    if self.should_buy(code, latest_data, ctx, precomputed_score=score):
                        buy_signals.append((code, score))
        else:
            # 如果没有指定当前交易日，则处理所有股票的最新数据（兼容旧的逻辑）
            for code in prepared_df["code"].unique():
                code_data = prepared_df[prepared_df["code"] == code]
                
                if code_data.empty:
                    continue
                
                latest_data = code_data.iloc[-1]
                
                # 硬筛选：与选股模块保持一致（仅对未持仓股票做筛选）
                if code not in ctx.positions:
                    if not self.filter_stock(latest_data, code_data):
                        continue
                
                score = self.score_stock(code, code_data)
                scores[code] = score
                
                if code in ctx.positions:
                    position = ctx.positions[code]
                    should_sell_flag, sell_reason = self.should_sell(code, latest_data, position, ctx)
                    if should_sell_flag:
                        sell_signals.append((code, sell_reason))
                else:
                    if self.should_buy(code, latest_data, ctx, precomputed_score=score):
                        buy_signals.append((code, score))
        
        buy_signals.sort(key=lambda x: x[1], reverse=True)
        
        result = {
            "buy_signals": buy_signals,  # list of (code, score) — 保留 score 供 backtest 引擎记录
            "sell_signals": sell_signals,  # list of (code, sell_reason)
            "scores": scores,
            "prepared_data": prepared_df,
        }
        
        self.logger.info(
            "Strategy execution completed",
            buy_count=len(buy_signals),
            sell_count=len(sell_signals),
            total_stocks=len(scores),
        )
        
        return result
    
    def _validate_no_future_data(self, daily_data: pd.Series) -> None:
        if "date" in daily_data.index:
            data_date = daily_data["date"]
            if isinstance(data_date, str):
                data_date = pd.to_datetime(data_date)
            
            if data_date > datetime.now():
                raise ValueError(f"Future date detected: {data_date}")
    
    def get_strategy_info(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "max_position_pct": self.max_position_pct,
            "max_positions": self.max_positions,
            "min_score_threshold": self.min_score_threshold,
            "min_holding_days": self._min_holding_days,
            "max_buy_per_day": self.max_buy_per_day,
            "max_sell_per_day": self.max_sell_per_day,
            "trailing_stop_drawdown": self._trailing_stop_drawdown,
            "trailing_stop_drawdown_core": self._trailing_stop_drawdown_core,
            "core_position_count": self._core_position_count,
            "time_stop_days": self._time_stop_days,
            "cooldown_map": self._cooldown_map,
        }