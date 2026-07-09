"""
选股路由：运行选股策略
"""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api.deps import get_raw_data_path
from src.api.schemas import SelectionRunResponse, SelectionResultItem
from src.data.providers.akshare_provider import AKShareProvider
from src.strategy.selection_strategy import SelectionConfig, SelectionStrategy
from src.core.logger import get_logger

router = APIRouter(prefix="/api/selection", tags=["Selection"])
logger = get_logger("API-Selection")


@router.post("/run", response_model=SelectionRunResponse)
async def run_selection():
    raw_path = get_raw_data_path()

    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="原始数据目录不存在，请先下载数据")

    raw_files = list(raw_path.glob("*.parquet"))
    if not raw_files:
        raise HTTPException(status_code=404, detail="暂无已下载的股票数据，请先下载数据")

    if not AKShareProvider._cache_loaded:
        try:
            import akshare as ak
            df_stocks = ak.stock_info_a_code_name()
            for _, row in df_stocks.iterrows():
                code = row.get("code", "")
                name = row.get("name", "")
                if code and name:
                    AKShareProvider._stock_name_cache[code] = name
            AKShareProvider._cache_loaded = True
        except Exception:
            pass

    selection_config = SelectionConfig.from_config()
    strategy = SelectionStrategy(selection_config)

    results = []
    total_scanned = 0

    for file in raw_files:
        try:
            df = pd.read_parquet(file)
            if df.empty:
                continue

            df["date"] = pd.to_datetime(df["date"])
            total_scanned += 1

            stock_name = ""
            if "name" in df.columns and not df.empty:
                stock_name = df.iloc[0].get("name", "")

            if not stock_name:
                pure_code = file.stem.split(".")[0]
                stock_name = AKShareProvider._stock_name_cache.get(pure_code, "")

            df = strategy.prepare(df)
            df_recent = df.tail(selection_config.limit_stat_period)
            latest = df.iloc[-1]

            if not strategy.filter_stock(latest, df):
                continue

            score = strategy.score_stock(file.stem, df_recent)

            latest_close = float(latest.get("close_price", 0))
            latest_pct_chg = latest.get("pct_chg", 0)

            try:
                latest_pct_chg = float(latest_pct_chg) if latest_pct_chg else 0.0
            except (ValueError, TypeError):
                latest_pct_chg = 0.0

            results.append(SelectionResultItem(
                code=file.stem,
                name=stock_name,
                score=round(score, 2),
                close_price=latest_close,
                pct_chg=round(latest_pct_chg, 2),
                tradable=-10 <= latest_pct_chg <= 10,
            ))
        except Exception as e:
            logger.warning(f"Failed to process {file.stem}: {e}")
            continue

    results.sort(key=lambda x: x.score, reverse=True)
    results = results[: selection_config.top_n]

    avg_score = sum(r.score for r in results) / len(results) if results else 0.0
    tradable_count = sum(1 for r in results if r.tradable)

    return SelectionRunResponse(
        total_scanned=total_scanned,
        total_selected=len(results),
        avg_score=round(avg_score, 2),
        tradable_count=tradable_count,
        results=results,
    )
