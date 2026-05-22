from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import numpy as np
import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger
from src.strategy.base_strategy import BaseStrategy, Position, StrategyContext


@dataclass
class Transaction:
    date: datetime
    code: str
    action: Literal["BUY", "SELL"]
    price: float
    shares: int
    commission: float
    amount: float
    reason: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "code": self.code,
            "action": self.action,
            "price": self.price,
            "shares": self.shares,
            "commission": self.commission,
            "amount": self.amount,
            "reason": self.reason,
        }


@dataclass
class PortfolioState:
    date: datetime
    capital: float
    positions_value: float
    positions: dict[str, Position]
    total_value: float
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "capital": self.capital,
            "positions_value": self.positions_value,
            "positions": {code: pos.shares for code, pos in self.positions.items()},
            "total_value": self.total_value,
        }


@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    transactions: list[Transaction] = field(default_factory=list)
    portfolio_states: list[PortfolioState] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
        }


class BacktestEngine:
    
    def __init__(
        self,
        strategy: BaseStrategy,
        initial_cash: float | None = None,
        commission_rate: float | None = None,
        stamp_duty_rate: float | None = None,
        min_commission: float | None = None,
    ):
        config = config_loader.get("backtest", {})
        
        self.strategy = strategy
        self.initial_cash = initial_cash or config.get("initial_cash", 1000000.0)
        self.commission_rate = commission_rate or config.get("commission_rate", 0.0003)
        self.stamp_duty_rate = stamp_duty_rate or config.get("stamp_duty_rate", 0.001)
        self.min_commission = min_commission or config.get("min_commission", 5.0)
        self.trading_days_per_year = config.get("trading_days_per_year", 252)
        
        self.logger = get_logger(self.__class__.__name__)
        
        self.capital = self.initial_cash
        self.positions: dict[str, Position] = {}
        self.transactions: list[Transaction] = []
        self.portfolio_states: list[PortfolioState] = []
    
    def run(self, df: pd.DataFrame) -> BacktestResult:
        self.logger.info(
            "Starting backtest",
            initial_cash=self.initial_cash,
            strategy=self.strategy.strategy_name,
        )
        
        self._validate_data(df)
        
        dates = sorted(df["date"].unique())
        
        for date in dates:
            self._process_date(df, date)
        
        result = self._calculate_result()
        
        self.logger.info(
            "Backtest completed",
            total_return=result.total_return,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=result.sharpe_ratio,
        )
        
        return result
    
    def _validate_data(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise ValueError("DataFrame is empty")
        
        required_fields = ["date", "code", "close_price"]
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        if df["date"].isna().any():
            raise ValueError("Date field contains missing values")
        
        now = datetime.now()
        future_dates = df["date"] > now
        if future_dates.any():
            raise ValueError(f"Found {future_dates.sum()} future dates")
    
    def _process_date(self, df: pd.DataFrame, date: datetime) -> None:
        date_df = df[df["date"] == date].copy()
        
        if date_df.empty:
            return
        
        ctx = StrategyContext(
            date=date,
            available_cash=self.capital,
            positions=self.positions.copy(),
            total_assets=self._calculate_total_value(date_df),
        )
        
        result = self.strategy.execute(date_df, ctx)
        
        for code in result["sell_signals"]:
            self._execute_sell(code, date_df, date)
        
        for code in result["buy_signals"]:
            self._execute_buy(code, date_df, date)
        
        self._record_portfolio_state(date, date_df)
    
    def _execute_sell(self, code: str, date_df: pd.DataFrame, date: datetime) -> None:
        if code not in self.positions:
            return
        
        position = self.positions[code]
        
        stock_data = date_df[date_df["code"] == code]
        if stock_data.empty:
            return
        
        price = stock_data.iloc[0]["close_price"]
        shares = position.shares
        
        amount = price * shares
        commission = max(amount * self.commission_rate, self.min_commission)
        stamp_duty = amount * self.stamp_duty_rate
        
        total_cost = commission + stamp_duty
        
        self.capital += amount - total_cost
        
        transaction = Transaction(
            date=date,
            code=code,
            action="SELL",
            price=price,
            shares=int(shares),
            commission=total_cost,
            amount=amount,
            reason="Strategy signal",
        )
        self.transactions.append(transaction)
        
        del self.positions[code]
        
        self.logger.info(
            "Executed sell",
            code=code,
            price=price,
            shares=shares,
            amount=amount,
        )
    
    def _execute_buy(self, code: str, date_df: pd.DataFrame, date: datetime) -> None:
        if code in self.positions:
            return
        
        stock_data = date_df[date_df["code"] == code]
        if stock_data.empty:
            return
        
        price = stock_data.iloc[0]["close_price"]
        
        max_position_value = self.capital * self.strategy.max_position_pct / 100
        max_shares = int(max_position_value / price / 100) * 100
        
        if max_shares == 0:
            return
        
        amount = price * max_shares
        commission = max(amount * self.commission_rate, self.min_commission)
        
        total_cost = amount + commission
        
        if total_cost > self.capital:
            return
        
        self.capital -= total_cost
        
        position = Position(
            code=code,
            shares=float(max_shares),
            cost_price=price,
            current_price=price,
            buy_date=date,
            holding_days=0,
        )
        self.positions[code] = position
        
        transaction = Transaction(
            date=date,
            code=code,
            action="BUY",
            price=price,
            shares=max_shares,
            commission=commission,
            amount=amount,
            reason="Strategy signal",
        )
        self.transactions.append(transaction)
        
        self.logger.info(
            "Executed buy",
            code=code,
            price=price,
            shares=max_shares,
            amount=amount,
        )
    
    def _calculate_total_value(self, date_df: pd.DataFrame) -> float:
        positions_value = 0.0
        
        for code, position in self.positions.items():
            stock_data = date_df[date_df["code"] == code]
            if not stock_data.empty:
                current_price = stock_data.iloc[0]["close_price"]
                positions_value += position.shares * current_price
        
        return self.capital + positions_value
    
    def _record_portfolio_state(self, date: datetime, date_df: pd.DataFrame) -> None:
        positions_value = 0.0
        
        for code, position in self.positions.items():
            stock_data = date_df[date_df["code"] == code]
            if not stock_data.empty:
                current_price = stock_data.iloc[0]["close_price"]
                position.current_price = current_price
                positions_value += position.shares * current_price
        
        total_value = self.capital + positions_value
        
        state = PortfolioState(
            date=date,
            capital=self.capital,
            positions_value=positions_value,
            positions=self.positions.copy(),
            total_value=total_value,
        )
        self.portfolio_states.append(state)
    
    def _calculate_result(self) -> BacktestResult:
        if not self.portfolio_states:
            return BacktestResult(
                total_return=0.0,
                annual_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
            )
        
        final_value = self.portfolio_states[-1].total_value
        total_return = (final_value - self.initial_cash) / self.initial_cash * 100
        
        days = len(self.portfolio_states)
        annual_return = 0.0
        if days > 0:
            annual_return = (pow(final_value / self.initial_cash, self.trading_days_per_year / days) - 1) * 100
        
        max_drawdown = self._calculate_max_drawdown()
        
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        win_rate, winning_trades, losing_trades = self._calculate_win_rate()
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=len(self.transactions),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            transactions=self.transactions,
            portfolio_states=self.portfolio_states,
        )
    
    def _calculate_max_drawdown(self) -> float:
        if not self.portfolio_states:
            return 0.0
        
        values = [state.total_value for state in self.portfolio_states]
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_sharpe_ratio(self) -> float:
        if len(self.portfolio_states) < 2:
            return 0.0
        
        values = [state.total_value for state in self.portfolio_states]
        returns = []
        
        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        sharpe = mean_return / std_return * np.sqrt(252)
        
        return sharpe
    
    def _calculate_win_rate(self) -> tuple[float, int, int]:
        if not self.transactions:
            return 0.0, 0, 0
        
        buy_sell_pairs = []
        buy_transactions = {}
        
        for trans in self.transactions:
            if trans.action == "BUY":
                if trans.code not in buy_transactions:
                    buy_transactions[trans.code] = []
                buy_transactions[trans.code].append(trans)
            elif trans.action == "SELL":
                if trans.code in buy_transactions and buy_transactions[trans.code]:
                    buy_trans = buy_transactions[trans.code].pop(0)
                    profit = (trans.price - buy_trans.price) * trans.shares
                    buy_sell_pairs.append(profit)
        
        if not buy_sell_pairs:
            return 0.0, 0, 0
        
        winning_trades = sum(1 for profit in buy_sell_pairs if profit > 0)
        losing_trades = sum(1 for profit in buy_sell_pairs if profit < 0)
        
        win_rate = winning_trades / len(buy_sell_pairs) * 100
        
        return win_rate, winning_trades, losing_trades
    
    def save_transaction_history(self, output_path: str = "./logs/transaction_history.parquet") -> None:
        if not self.transactions:
            self.logger.warning("No transactions to save")
            return
        
        df = pd.DataFrame([trans.to_dict() for trans in self.transactions])
        
        df.to_parquet(output_path, compression="snappy", index=False)
        
        self.logger.info(
            "Transaction history saved",
            file_path=output_path,
            count=len(self.transactions),
        )
    
    def save_portfolio_states(self, output_path: str = "./logs/portfolio_states.parquet") -> None:
        if not self.portfolio_states:
            self.logger.warning("No portfolio states to save")
            return
        
        records = []
        for state in self.portfolio_states:
            record = {
                "date": state.date,
                "capital": state.capital,
                "positions_value": state.positions_value,
                "total_value": state.total_value,
                "positions_count": len(state.positions),
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        df.to_parquet(output_path, compression="snappy", index=False)
        
        self.logger.info(
            "Portfolio states saved",
            file_path=output_path,
            count=len(self.portfolio_states),
        )