from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger


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
        
        self.strategy_name = strategy_name or self.__class__.__name__
        self.logger = get_logger(self.strategy_name)
        
        self.stop_loss_pct = config.get("stop_loss_pct", -8.0)
        self.take_profit_pct = config.get("take_profit_pct", 20.0)
        self.max_position_pct = config.get("max_position_pct", 30.0)
        self.max_positions = config.get("max_positions", 10)
        self.min_score_threshold = config.get("min_score_threshold", 60.0)
        
        self._prepared_data: pd.DataFrame | None = None
    
    @abstractmethod
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        pass
    
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
        
        score = self.score_stock(code, daily_data)
        
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
    
    def execute(self, df: pd.DataFrame, ctx: StrategyContext) -> dict[str, Any]:
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
        
        for code in prepared_df["code"].unique():
            code_data = prepared_df[prepared_df["code"] == code]
            
            if code_data.empty:
                continue
            
            latest_data = code_data.iloc[-1]
            
            score = self.score_stock(code, latest_data)
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