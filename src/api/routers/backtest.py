"""
回测路由：运行回测
"""

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api.deps import get_raw_data_path
from src.api.schemas import BacktestRunRequest, BacktestResultResponse, TransactionItem, PortfolioStateItem
from src.backtest.backtest_engine import BacktestEngine
from src.strategy.selection_strategy import SelectionStrategy, SelectionConfig
from src.core.logger import get_logger

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])
logger = get_logger("API-Backtest")


@router.post("/run", response_model=BacktestResultResponse)
async def run_backtest(req: BacktestRunRequest):
    raw_path = get_raw_data_path()

    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="原始数据目录不存在，请先下载数据")

    raw_files = list(raw_path.glob("*.parquet"))
    if not raw_files:
        raise HTTPException(status_code=404, detail="暂无已下载的股票数据，请先下载数据")

    all_data = []
    for file_path in raw_files:
        try:
            df = pd.read_parquet(file_path)
            if df.empty:
                continue
            df["date"] = pd.to_datetime(df["date"])
            df = df[
                (df["date"] >= pd.Timestamp(req.start_date))
                & (df["date"] <= pd.Timestamp(req.end_date))
            ]
            if not df.empty:
                all_data.append(df)
        except Exception as e:
            logger.warning(f"Failed to read {file_path.name}: {e}")
            continue

    if not all_data:
        raise HTTPException(status_code=400, detail="没有找到符合回测时间范围的数据")

    combined_df = pd.concat(all_data, ignore_index=True)

    selection_config = SelectionConfig.from_config()
    selection_config.initial_cash = req.initial_cash
    selection_config.max_positions = req.max_positions

    strategy = SelectionStrategy(selection_config)
    strategy.stop_loss_pct = req.stop_loss_pct
    strategy.take_profit_pct = req.take_profit_pct

    engine = BacktestEngine(
        strategy=strategy,
        initial_cash=req.initial_cash,
    )

    try:
        result = engine.run(combined_df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测执行失败: {str(e)}")

    transactions = [
        TransactionItem(
            date=trans.date.strftime("%Y-%m-%d"),
            code=trans.code,
            action=trans.action,
            price=trans.price,
            shares=trans.shares,
            amount=trans.amount,
            commission=trans.commission,
            profit=trans.profit,
            total_value=trans.total_value,
            reason=trans.reason,
        )
        for trans in result.transactions
    ]

    portfolio_states = [
        PortfolioStateItem(
            date=state.date.strftime("%Y-%m-%d") if hasattr(state.date, "strftime") else str(state.date),
            capital=state.capital,
            positions_value=state.positions_value,
            total_value=state.total_value,
        )
        for state in result.portfolio_states
    ]

    return BacktestResultResponse(
        total_return=round(result.total_return, 2),
        annual_return=round(result.annual_return, 2),
        max_drawdown=round(result.max_drawdown, 2),
        sharpe_ratio=round(result.sharpe_ratio, 2),
        win_rate=round(result.win_rate, 2),
        total_trades=result.total_trades,
        winning_trades=result.winning_trades,
        losing_trades=result.losing_trades,
        total_slippage_cost=round(result.total_slippage_cost, 2),
        transactions=transactions,
        portfolio_states=portfolio_states,
    )
