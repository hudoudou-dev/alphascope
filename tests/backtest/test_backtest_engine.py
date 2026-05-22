from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.backtest.backtest_engine import BacktestEngine, BacktestResult, PortfolioState, Transaction
from src.strategy.base_strategy import BaseStrategy, Position, StrategyContext


class SimpleTestStrategy(BaseStrategy):
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        return 70.0


@pytest.fixture
def sample_backtest_data() -> pd.DataFrame:
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    
    data = []
    for i, date in enumerate(dates):
        base_price = 10.0 + i * 0.1
        data.append({
            "date": date,
            "open_price": base_price,
            "high_price": base_price + 0.5,
            "low_price": base_price - 0.5,
            "close_price": base_price + 0.2,
            "volume": 1000000.0,
            "amount": 10000000.0,
            "code": "600000.SH",
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_strategy() -> BaseStrategy:
    return SimpleTestStrategy()


class TestBacktestEngine:
    
    def test_init(self, sample_strategy: BaseStrategy):
        engine = BacktestEngine(strategy=sample_strategy)
        
        assert engine.initial_cash == 1000000.0
        assert engine.commission_rate == 0.0003
        assert engine.stamp_duty_rate == 0.001
        assert engine.capital == 1000000.0
    
    def test_validate_data(self, sample_strategy: BaseStrategy, sample_backtest_data: pd.DataFrame):
        engine = BacktestEngine(strategy=sample_strategy)
        
        engine._validate_data(sample_backtest_data)
    
    def test_validate_empty_data(self, sample_strategy: BaseStrategy):
        engine = BacktestEngine(strategy=sample_strategy)
        
        with pytest.raises(ValueError, match="DataFrame is empty"):
            engine._validate_data(pd.DataFrame())
    
    def test_validate_missing_fields(self, sample_strategy: BaseStrategy):
        engine = BacktestEngine(strategy=sample_strategy)
        
        df = pd.DataFrame({"date": [datetime.now()]})
        
        with pytest.raises(ValueError, match="Missing required fields"):
            engine._validate_data(df)
    
    def test_validate_future_dates(self, sample_strategy: BaseStrategy):
        engine = BacktestEngine(strategy=sample_strategy)
        
        df = pd.DataFrame({
            "date": [datetime.now() + timedelta(days=10)],
            "code": ["600000.SH"],
            "close_price": [10.0],
        })
        
        with pytest.raises(ValueError, match="future dates"):
            engine._validate_data(df)
    
    def test_run_backtest(self, sample_strategy: BaseStrategy, sample_backtest_data: pd.DataFrame):
        engine = BacktestEngine(strategy=sample_strategy, initial_cash=100000.0)
        
        result = engine.run(sample_backtest_data)
        
        assert isinstance(result, BacktestResult)
        assert isinstance(result.total_return, float)
        assert isinstance(result.annual_return, float)
        assert isinstance(result.max_drawdown, float)
        assert isinstance(result.sharpe_ratio, float)
    
    def test_execute_buy(self, sample_strategy: BaseStrategy, sample_backtest_data: pd.DataFrame):
        engine = BacktestEngine(strategy=sample_strategy, initial_cash=100000.0)
        
        date = sample_backtest_data["date"].iloc[0]
        date_df = sample_backtest_data[sample_backtest_data["date"] == date]
        
        engine._execute_buy("600000.SH", date_df, date)
        
        assert "600000.SH" in engine.positions
        assert len(engine.transactions) == 1
        assert engine.transactions[0].action == "BUY"
    
    def test_execute_sell(self, sample_strategy: BaseStrategy, sample_backtest_data: pd.DataFrame):
        engine = BacktestEngine(strategy=sample_strategy, initial_cash=100000.0)
        
        date = sample_backtest_data["date"].iloc[0]
        date_df = sample_backtest_data[sample_backtest_data["date"] == date]
        
        engine._execute_buy("600000.SH", date_df, date)
        
        sell_date = sample_backtest_data["date"].iloc[5]
        sell_df = sample_backtest_data[sample_backtest_data["date"] == sell_date]
        
        engine._execute_sell("600000.SH", sell_df, sell_date)
        
        assert "600000.SH" not in engine.positions
        assert len(engine.transactions) == 2
        assert engine.transactions[1].action == "SELL"
    
    def test_calculate_total_value(self, sample_strategy: BaseStrategy, sample_backtest_data: pd.DataFrame):
        engine = BacktestEngine(strategy=sample_strategy, initial_cash=100000.0)
        
        date = sample_backtest_data["date"].iloc[0]
        date_df = sample_backtest_data[sample_backtest_data["date"] == date]
        
        engine._execute_buy("600000.SH", date_df, date)
        
        total_value = engine._calculate_total_value(date_df)
        
        assert total_value > 0
    
    def test_record_portfolio_state(self, sample_strategy: BaseStrategy, sample_backtest_data: pd.DataFrame):
        engine = BacktestEngine(strategy=sample_strategy, initial_cash=100000.0)
        
        date = sample_backtest_data["date"].iloc[0]
        date_df = sample_backtest_data[sample_backtest_data["date"] == date]
        
        engine._record_portfolio_state(date, date_df)
        
        assert len(engine.portfolio_states) == 1
        assert engine.portfolio_states[0].date == date
    
    def test_calculate_max_drawdown(self, sample_strategy: BaseStrategy):
        engine = BacktestEngine(strategy=sample_strategy)
        
        values = [100, 110, 105, 115, 100, 120]
        engine.portfolio_states = [
            PortfolioState(
                date=datetime(2024, 1, i+1),
                capital=v,
                positions_value=0,
                positions={},
                total_value=v,
            )
            for i, v in enumerate(values)
        ]
        
        max_dd = engine._calculate_max_drawdown()
        
        assert max_dd >= 0
    
    def test_calculate_sharpe_ratio(self, sample_strategy: BaseStrategy):
        engine = BacktestEngine(strategy=sample_strategy)
        
        values = [100, 101, 102, 103, 104, 105]
        engine.portfolio_states = [
            PortfolioState(
                date=datetime(2024, 1, i+1),
                capital=v,
                positions_value=0,
                positions={},
                total_value=v,
            )
            for i, v in enumerate(values)
        ]
        
        sharpe = engine._calculate_sharpe_ratio()
        
        assert isinstance(sharpe, float)
    
    def test_calculate_win_rate(self, sample_strategy: BaseStrategy):
        engine = BacktestEngine(strategy=sample_strategy)
        
        engine.transactions = [
            Transaction(date=datetime(2024, 1, 1), code="600000.SH", action="BUY", price=10.0, shares=100, commission=5.0, amount=1000.0),
            Transaction(date=datetime(2024, 1, 2), code="600000.SH", action="SELL", price=11.0, shares=100, commission=5.0, amount=1100.0),
            Transaction(date=datetime(2024, 1, 3), code="000001.SZ", action="BUY", price=20.0, shares=100, commission=5.0, amount=2000.0),
            Transaction(date=datetime(2024, 1, 4), code="000001.SZ", action="SELL", price=19.0, shares=100, commission=5.0, amount=1900.0),
        ]
        
        win_rate, winning, losing = engine._calculate_win_rate()
        
        assert win_rate == 50.0
        assert winning == 1
        assert losing == 1
    
    def test_save_transaction_history(self, sample_strategy: BaseStrategy, tmp_path: Path):
        engine = BacktestEngine(strategy=sample_strategy)
        
        engine.transactions = [
            Transaction(date=datetime(2024, 1, 1), code="600000.SH", action="BUY", price=10.0, shares=100, commission=5.0, amount=1000.0),
        ]
        
        output_path = tmp_path / "transaction_history.parquet"
        engine.save_transaction_history(str(output_path))
        
        assert output_path.exists()
    
    def test_save_portfolio_states(self, sample_strategy: BaseStrategy, tmp_path: Path):
        engine = BacktestEngine(strategy=sample_strategy)
        
        engine.portfolio_states = [
            PortfolioState(
                date=datetime(2024, 1, 1),
                capital=100000.0,
                positions_value=0,
                positions={},
                total_value=100000.0,
            ),
        ]
        
        output_path = tmp_path / "portfolio_states.parquet"
        engine.save_portfolio_states(str(output_path))
        
        assert output_path.exists()


class TestTransaction:
    
    def test_transaction_to_dict(self):
        trans = Transaction(
            date=datetime(2024, 1, 1),
            code="600000.SH",
            action="BUY",
            price=10.0,
            shares=100,
            commission=5.0,
            amount=1000.0,
        )
        
        result = trans.to_dict()
        
        assert result["code"] == "600000.SH"
        assert result["action"] == "BUY"
        assert result["price"] == 10.0


class TestPortfolioState:
    
    def test_portfolio_state_to_dict(self):
        state = PortfolioState(
            date=datetime(2024, 1, 1),
            capital=100000.0,
            positions_value=50000.0,
            positions={},
            total_value=150000.0,
        )
        
        result = state.to_dict()
        
        assert result["capital"] == 100000.0
        assert result["total_value"] == 150000.0


class TestBacktestResult:
    
    def test_backtest_result_to_dict(self):
        result = BacktestResult(
            total_return=10.0,
            annual_return=20.0,
            max_drawdown=5.0,
            sharpe_ratio=1.5,
            win_rate=60.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["total_return"] == 10.0
        assert result_dict["sharpe_ratio"] == 1.5