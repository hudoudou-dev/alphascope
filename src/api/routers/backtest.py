"""
回测路由：运行回测（异步任务模式）
- POST /api/backtest/run        → 提交任务，返回 task_id
- GET  /api/backtest/status/{id} → 查询任务进度
- GET  /api/backtest/result/{id} → 获取已完成任务的结果
"""

import uuid
import threading
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api.deps import get_raw_data_path
from src.api.schemas import (
    BacktestRunRequest,
    BacktestTaskResponse,
    BacktestTaskStatusResponse,
    BacktestResultResponse,
    TransactionItem,
    PortfolioStateItem,
)
from src.backtest.backtest_engine import BacktestEngine
from src.strategy.selection_strategy import SelectionStrategy, SelectionConfig
from src.core.logger import get_logger

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])
logger = get_logger("API-Backtest")

# ---------------------------------------------------------------------------
# 任务管理器：内存字典 + 线程锁
# ---------------------------------------------------------------------------

_tasks: dict[str, dict] = {}
_lock = threading.Lock()

MAX_TASKS = 20  # 保留最近的任务记录，防止内存泄漏


def _task_key() -> str:
    return uuid.uuid4().hex[:12]


def _set_task(task_id: str, **kwargs):
    with _lock:
        if task_id not in _tasks:
            _tasks[task_id] = {}
        _tasks[task_id].update(kwargs)
        # 清理过期任务（保留最近 MAX_TASKS 条）
        if len(_tasks) > MAX_TASKS:
            stale = sorted(_tasks.keys())[: len(_tasks) - MAX_TASKS]
            for k in stale:
                _tasks.pop(k, None)


def _get_task(task_id: str) -> Optional[dict]:
    with _lock:
        return _tasks.get(task_id)


# ---------------------------------------------------------------------------
# 核心回测执行（后台线程）
# ---------------------------------------------------------------------------

def _run_backtest_task(task_id: str, req: BacktestRunRequest):
    """在后台线程中执行回测，通过 progress_callback 更新任务状态"""
    try:
        _set_task(task_id, status="running", progress=0, message="正在加载数据...")

        # --- 阶段1：加载数据（0%-20%）---
        raw_path = get_raw_data_path()
        if not raw_path.exists():
            _set_task(task_id, status="failed", error="原始数据目录不存在，请先下载数据")
            return

        raw_files = list(raw_path.glob("*.parquet"))
        if not raw_files:
            _set_task(task_id, status="failed", error="暂无已下载的股票数据，请先下载数据")
            return

        all_data = []
        total_files = len(raw_files)
        for idx, file_path in enumerate(raw_files):
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

            # 更新加载进度（0 → 20%）
            pct = int((idx + 1) / total_files * 20)
            _set_task(task_id, progress=pct, message=f"加载数据: {idx + 1}/{total_files}")

        if not all_data:
            _set_task(task_id, status="failed", error="没有找到符合回测时间范围的数据")
            return

        combined_df = pd.concat(all_data, ignore_index=True)
        num_dates = combined_df["date"].nunique()
        logger.info(f"Backtest task {task_id}: loaded {len(all_data)} stocks, {num_dates} trading days")

        # --- 阶段2：构建策略与引擎 ---
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

        # --- 阶段3：执行回测（20%-100%）---
        def progress_callback(current: int, total: int):
            pct = 20 + int(current / total * 80) if total > 0 else 100
            _set_task(
                task_id,
                progress=pct,
                message=f"回测进行中: {current}/{total} 个交易日 ({pct}%)",
            )

        result = engine.run(combined_df, progress_callback=progress_callback)

        # --- 阶段4：序列化结果 ---
        _set_task(task_id, progress=100, message="正在整理结果...")

        transactions = [
            TransactionItem(
                date=trans.date.strftime("%Y-%m-%d"),
                code=trans.code,
                name=trans.name,
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

        final_result = BacktestResultResponse(
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

        _set_task(
            task_id,
            status="completed",
            progress=100,
            message="回测完成",
            result=final_result,
        )
        logger.info(f"Backtest task {task_id}: completed, return={final_result.total_return}%")

    except Exception as e:
        logger.error(f"Backtest task {task_id} failed: {e}", exc_info=True)
        _set_task(task_id, status="failed", error=str(e))


# ---------------------------------------------------------------------------
# API 端点
# ---------------------------------------------------------------------------

@router.post("/run", response_model=BacktestTaskResponse)
async def submit_backtest(req: BacktestRunRequest):
    """提交回测任务，立即返回 task_id，后台执行"""
    raw_path = get_raw_data_path()
    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="原始数据目录不存在，请先下载数据")
    if not list(raw_path.glob("*.parquet")):
        raise HTTPException(status_code=404, detail="暂无已下载的股票数据，请先下载数据")

    task_id = _task_key()
    _set_task(task_id, status="pending", progress=0, message="任务已提交，等待执行...")

    thread = threading.Thread(
        target=_run_backtest_task,
        args=(task_id, req),
        daemon=True,
        name=f"backtest-{task_id}",
    )
    thread.start()

    logger.info(f"Backtest task submitted: {task_id}")
    return BacktestTaskResponse(
        task_id=task_id,
        status="submitted",
        message="回测任务已提交，正在后台执行",
    )


@router.get("/status/{task_id}", response_model=BacktestTaskStatusResponse)
async def get_backtest_status(task_id: str):
    """查询回测任务的状态和进度"""
    task = _get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return BacktestTaskStatusResponse(
        task_id=task_id,
        status=task.get("status", "unknown"),
        progress=task.get("progress", 0),
        message=task.get("message", ""),
        error=task.get("error"),
    )


@router.get("/result/{task_id}", response_model=BacktestResultResponse)
async def get_backtest_result(task_id: str):
    """获取已完成回测任务的结果"""
    task = _get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    status = task.get("status")
    if status == "pending" or status == "running":
        raise HTTPException(status_code=202, detail=f"任务仍在执行中，当前进度: {task.get('progress', 0)}%")
    if status == "failed":
        raise HTTPException(status_code=500, detail=task.get("error", "回测执行失败"))

    result = task.get("result")
    if result is None:
        raise HTTPException(status_code=500, detail="任务已完成但无结果数据")

    return result
