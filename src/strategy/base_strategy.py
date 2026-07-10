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
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def profit_loss(self) -> float:
        return (self.current_price - self.cost_price) / self.cost_price * 100


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
        
        self.strategy_name = strategy_name or self.__class__.__name__
        self.logger = get_logger(self.strategy_name)
        
        self.stop_loss_pct = config.get("stop_loss_pct", -8.0)
        self.take_profit_pct = config.get("take_profit_pct", 20.0)
        self.max_position_pct = config.get("max_position_pct", 30.0)
        self.max_positions = config.get("max_positions", 10)
        self.min_score_threshold = selection_config.get("min_score_threshold", 50.0)
        
        # 交易频率控制
        self.cooldown_days = selection_config.get("cooldown_days", 5)
        self.max_trades_per_day = selection_config.get("max_trades_per_day", 5)
        
        # 记录每只股票的最后卖出日期（用于冷却期）
        self._last_sell_dates: dict[str, datetime] = {}
        
        # 记录每天的交易次数（用于交易频率限制）
        self._daily_trade_counts: dict[str, int] = {}
        
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
                if compute_turn and "turn" not in group.columns and "volume" in group.columns:
                    avg_vol = group["volume"].rolling(window=20, min_periods=1).mean()
                    group["turn"] = (group["volume"] / avg_vol.replace(0, np.nan)) * 100
                result_frames.append(group)
            return pd.concat(result_frames, ignore_index=True)

        df["pct_chg"] = df["close_price"].pct_change() * 100
        df = tech.add_all_indicators(df)
        if compute_turn and "turn" not in df.columns and "volume" in df.columns:
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

    def should_buy(self, code: str, daily_data: pd.Series, ctx: StrategyContext) -> bool:
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
        
        # 检查冷却期
        if code in self._last_sell_dates:
            last_sell_date = self._last_sell_dates[code]
            days_since_sell = (ctx.date - last_sell_date).days
            if days_since_sell < self.cooldown_days:
                self.logger.debug(
                    "In cooldown period",
                    code=code,
                    days_since_sell=days_since_sell,
                    cooldown_days=self.cooldown_days,
                )
                return False
        
        # 检查交易频率限制
        date_str = ctx.date.strftime("%Y-%m-%d")
        if date_str in self._daily_trade_counts:
            if self._daily_trade_counts[date_str] >= self.max_trades_per_day:
                self.logger.debug(
                    "Max trades per day reached",
                    date=date_str,
                    trades=self._daily_trade_counts[date_str],
                    max_trades=self.max_trades_per_day,
                )
                return False
        
        # 从self._prepared_data中获取该股票的历史数据
        if self._prepared_data is not None:
            code_data = self._prepared_data[self._prepared_data["code"] == code]
            score = self.score_stock(code, code_data)
        else:
            # 如果没有准备数据，使用默认评分
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
    
    def should_sell(self, code: str, daily_data: pd.Series, position: Position, ctx: StrategyContext) -> bool:
        self._validate_no_future_data(daily_data)
        
        if code not in ctx.positions:
            return False
        
        current_price = daily_data.get("close_price", position.current_price)
        profit_loss = (current_price - position.cost_price) / position.cost_price * 100
        
        if profit_loss <= self.stop_loss_pct:
            self.logger.warning(
                "Stop loss triggered",
                code=code,
                profit_loss=profit_loss,
                stop_loss=self.stop_loss_pct,
            )
            return True
        
        if profit_loss >= self.take_profit_pct:
            self.logger.info(
                "Take profit triggered",
                code=code,
                profit_loss=profit_loss,
                take_profit=self.take_profit_pct,
            )
            return True
        
        sell_signal = self._check_sell_signal(code, daily_data, position, ctx)
        
        if sell_signal:
            self.logger.info(
                "Sell signal triggered",
                code=code,
                profit_loss=profit_loss,
                holding_days=position.holding_days,
            )
        
        return sell_signal
    
    def _check_sell_signal(
        self,
        code: str,
        daily_data: pd.Series,
        position: Position,
        ctx: StrategyContext,
    ) -> bool:
        return False
    
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
        buy_signals = []
        sell_signals = []
        
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
                
                # 计算评分（传入整个DataFrame，而不是只传入最新一天的数据）
                score = self.score_stock(code, code_data)
                scores[code] = score
                
                # 获取最新一天的数据
                latest_data = code_data.iloc[-1]
                
                if code in ctx.positions:
                    position = ctx.positions[code]
                    if self.should_sell(code, latest_data, position, ctx):
                        sell_signals.append(code)
                else:
                    if self.should_buy(code, latest_data, ctx):
                        buy_signals.append((code, score))
        else:
            # 如果没有指定当前交易日，则处理所有股票的最新数据（兼容旧的逻辑）
            for code in prepared_df["code"].unique():
                code_data = prepared_df[prepared_df["code"] == code]
                
                if code_data.empty:
                    continue
                
                latest_data = code_data.iloc[-1]
                
                score = self.score_stock(code, code_data)
                scores[code] = score
                
                if code in ctx.positions:
                    position = ctx.positions[code]
                    if self.should_sell(code, latest_data, position, ctx):
                        sell_signals.append(code)
                else:
                    if self.should_buy(code, latest_data, ctx):
                        buy_signals.append((code, score))
        
        buy_signals.sort(key=lambda x: x[1], reverse=True)
        
        result = {
            "buy_signals": [code for code, _ in buy_signals],
            "sell_signals": sell_signals,
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
        }