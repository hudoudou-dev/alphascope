from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.strategy.base_strategy import BaseStrategy, Position, StrategyContext


class ConcreteStrategy(BaseStrategy):
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        from src.indicators.technical_indicators import TechnicalIndicators
        
        indicators = TechnicalIndicators()
        return indicators.add_all_indicators(df)
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        from src.indicators.technical_indicators import TechnicalIndicators
        
        if self._prepared_data is None:
            return 50.0
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        if code_df.empty:
            return 50.0
        
        indicators = TechnicalIndicators()
        return indicators.calculate_composite_score(code_df)


@pytest.fixture
def sample_stock_data() -> pd.DataFrame:
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
            "volume": 1000000.0 + i * 10000,
            "amount": 10000000.0 + i * 100000,
            "code": "600000.SH",
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_position() -> Position:
    return Position(
        code="600000.SH",
        shares=100.0,
        cost_price=10.0,
        current_price=11.0,
        buy_date=datetime(2024, 1, 1),
        holding_days=10,
    )


@pytest.fixture
def sample_context(sample_position: Position) -> StrategyContext:
    return StrategyContext(
        date=datetime(2024, 1, 15),
        available_cash=100000.0,
        positions={"600000.SH": sample_position},
        total_assets=111000.0,
    )


class TestBaseStrategy:
    
    def test_init(self):
        strategy = ConcreteStrategy(strategy_name="TestStrategy")
        
        assert strategy.strategy_name == "TestStrategy"
        assert strategy.stop_loss_pct == -8.0
        assert strategy.take_profit_pct == 20.0
        assert strategy.max_position_pct == 30.0
        assert strategy.max_positions == 10
    
    def test_prepare(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        
        prepared_df = strategy.prepare(sample_stock_data)
        
        assert not prepared_df.empty
        assert "ma5" in prepared_df.columns
        assert "ma10" in prepared_df.columns
        assert "rsi" in prepared_df.columns
        assert "macd" in prepared_df.columns
    
    def test_score_stock(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        
        prepared_df = strategy.prepare(sample_stock_data)
        strategy._prepared_data = prepared_df
        
        latest_data = prepared_df.iloc[-1]
        score = strategy.score_stock("600000.SH", latest_data)
        
        assert 0 <= score <= 100
    
    def test_should_buy_success(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        
        prepared_df = strategy.prepare(sample_stock_data)
        strategy._prepared_data = prepared_df
        
        ctx = StrategyContext(
            date=datetime(2024, 1, 15),
            available_cash=100000.0,
            positions={},
            total_assets=100000.0,
        )
        
        latest_data = prepared_df.iloc[-1]
        
        result = strategy.should_buy("600000.SH", latest_data, ctx)
        
        assert isinstance(result, bool)
    
    def test_should_buy_insufficient_cash(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        
        prepared_df = strategy.prepare(sample_stock_data)
        strategy._prepared_data = prepared_df
        
        ctx = StrategyContext(
            date=datetime(2024, 1, 15),
            available_cash=0.0,
            positions={},
            total_assets=100000.0,
        )
        
        latest_data = prepared_df.iloc[-1]
        
        result = strategy.should_buy("600000.SH", latest_data, ctx)
        
        assert result is False
    
    def test_should_buy_max_positions_reached(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        
        prepared_df = strategy.prepare(sample_stock_data)
        strategy._prepared_data = prepared_df
        
        positions = {}
        for i in range(10):
            positions[f"stock{i}"] = Position(
                code=f"stock{i}",
                shares=100.0,
                cost_price=10.0,
                current_price=11.0,
                buy_date=datetime(2024, 1, 1),
            )
        
        ctx = StrategyContext(
            date=datetime(2024, 1, 15),
            available_cash=100000.0,
            positions=positions,
            total_assets=200000.0,
        )
        
        latest_data = prepared_df.iloc[-1]
        
        result = strategy.should_buy("600000.SH", latest_data, ctx)
        
        assert result is False
    
    def test_should_sell_stop_loss(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        strategy.stop_loss_pct = -5.0
        
        prepared_df = strategy.prepare(sample_stock_data)
        strategy._prepared_data = prepared_df
        
        position = Position(
            code="600000.SH",
            shares=100.0,
            cost_price=12.0,
            current_price=11.0,
            buy_date=datetime(2024, 1, 1),
            holding_days=10,
        )
        
        ctx = StrategyContext(
            date=datetime(2024, 1, 15),
            available_cash=100000.0,
            positions={"600000.SH": position},
            total_assets=111000.0,
        )
        
        latest_data = prepared_df.iloc[-1]
        latest_data["close_price"] = 11.0
        
        result = strategy.should_sell("600000.SH", latest_data, position, ctx)
        
        assert result is True
    
    def test_should_sell_take_profit(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        strategy.take_profit_pct = 10.0
        
        prepared_df = strategy.prepare(sample_stock_data)
        strategy._prepared_data = prepared_df
        
        position = Position(
            code="600000.SH",
            shares=100.0,
            cost_price=10.0,
            current_price=12.0,
            buy_date=datetime(2024, 1, 1),
            holding_days=10,
        )
        
        ctx = StrategyContext(
            date=datetime(2024, 1, 15),
            available_cash=100000.0,
            positions={"600000.SH": position},
            total_assets=122000.0,
        )
        
        latest_data = prepared_df.iloc[-1]
        latest_data["close_price"] = 12.0
        
        result = strategy.should_sell("600000.SH", latest_data, position, ctx)
        
        assert result is True
    
    def test_execute(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        
        ctx = StrategyContext(
            date=datetime(2024, 1, 15),
            available_cash=100000.0,
            positions={},
            total_assets=100000.0,
        )
        
        result = strategy.execute(sample_stock_data, ctx)
        
        assert "buy_signals" in result
        assert "sell_signals" in result
        assert "scores" in result
        assert isinstance(result["buy_signals"], list)
        assert isinstance(result["sell_signals"], list)
        assert isinstance(result["scores"], dict)
    
    def test_get_strategy_info(self):
        strategy = ConcreteStrategy(strategy_name="TestStrategy")
        
        info = strategy.get_strategy_info()
        
        assert info["strategy_name"] == "TestStrategy"
        assert "stop_loss_pct" in info
        assert "take_profit_pct" in info
        assert "max_position_pct" in info
    
    def test_validate_no_future_data(self, sample_stock_data: pd.DataFrame):
        strategy = ConcreteStrategy()
        
        future_data = sample_stock_data.iloc[-1].copy()
        future_data["date"] = datetime.now() + timedelta(days=10)
        
        with pytest.raises(ValueError, match="Future date detected"):
            strategy._validate_no_future_data(future_data)


class TestPosition:
    
    def test_position_properties(self, sample_position: Position):
        assert sample_position.market_value == 1100.0
        assert sample_position.profit_loss == 10.0
    
    def test_position_loss(self):
        position = Position(
            code="600000.SH",
            shares=100.0,
            cost_price=10.0,
            current_price=9.0,
            buy_date=datetime(2024, 1, 1),
        )
        
        assert position.profit_loss == -10.0


class TestStrategyContext:
    
    def test_context_properties(self, sample_context: StrategyContext):
        assert sample_context.position_value == 1100.0
        assert sample_context.total_assets == 111000.0