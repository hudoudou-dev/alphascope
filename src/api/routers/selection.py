"""
选股路由：运行选股策略
"""

from pathlib import Path

import numpy as np
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
    prepared: dict[str, tuple[pd.DataFrame, pd.Series, str]] = {}

    use_universe = selection_config.cross_sectional_enabled or selection_config.regime_enabled

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

            prepared[file.stem] = (df_recent, latest, stock_name)
        except Exception as e:
            logger.warning(f"Failed to process {file.stem}: {e}")
            continue

    # 横截面标准化 / 行情自适应：先在全市场层面一次性打分（默认关闭，不影响原路径）
    universe_scores: dict[str, dict] | None = None
    if use_universe and prepared:
        breadth = sum(
            1 for _, latest, _ in prepared.values()
            if latest.get("close_price", 0) > latest.get("ma20", 0)
        ) / len(prepared)
        has_vol = any(
            not pd.isna(latest.get("hist_vol", np.nan))
            for _, latest, _ in prepared.values()
        )
        avg_vol = float(np.nanmean([
            latest.get("hist_vol", np.nan)
            for _, latest, _ in prepared.values()
        ])) if has_vol else None
        universe_scores = strategy.score_universe(
            {code: d[0] for code, d in prepared.items()},
            breadth=breadth,
            avg_vol=avg_vol,
        )

    for code, (df_recent, latest, stock_name) in prepared.items():
        if universe_scores is not None:
            u = universe_scores.get(code)
            if u is None:
                continue
            score = u["score"]
            sub_scores = u["detail"]
            completeness = u["completeness"]
        else:
            score = strategy.score_stock(code, df_recent)
            sub_scores = strategy.get_last_detail_scores()
            completeness = strategy.get_last_completeness()

        latest_close = float(latest.get("close_price", 0))
        latest_pct_chg = latest.get("pct_chg", 0)

        try:
            latest_pct_chg = float(latest_pct_chg) if latest_pct_chg else 0.0
        except (ValueError, TypeError):
            latest_pct_chg = 0.0

        # 计算因子明细
        trend_detail = ""
        momentum_detail = ""
        volume_detail = ""
        vol_detail = ""
        fund_detail = ""

        try:
            rsi_val = latest.get("rsi", None)
            rsi_val_str = f"{float(rsi_val):.1f}" if rsi_val is not None and not pd.isna(rsi_val) else "-"

            macd_val = latest.get("macd", None)
            macd_sig = latest.get("macd_signal", None)
            if macd_val is not None and macd_sig is not None and not pd.isna(macd_val) and not pd.isna(macd_sig):
                trend_detail = f"MACD:{'金叉' if float(macd_val) > float(macd_sig) else '死叉'}"
            else:
                trend_detail = "-"

            momentum_detail = f"RSI:{rsi_val_str}"

            vol_ratio = latest.get("volume_ratio", None)
            volume_detail = f"量比:{float(vol_ratio):.1f}" if vol_ratio is not None and not pd.isna(vol_ratio) else "-"

            bb_pos = "-"
            bb_upper = latest.get("bb_upper", None)
            bb_lower = latest.get("bb_lower", None)
            if bb_upper is not None and bb_lower is not None and not pd.isna(bb_upper) and not pd.isna(bb_lower):
                bb_range = float(bb_upper) - float(bb_lower)
                if bb_range > 0:
                    pos = (latest_close - float(bb_lower)) / bb_range
                    if pos < 0.1:
                        bb_pos = "下轨"
                    elif pos > 0.9:
                        bb_pos = "上轨"
                    elif 0.4 <= pos <= 0.6:
                        bb_pos = "中轨"
                    else:
                        bb_pos = f"{pos*100:.0f}%"
            vol_detail = f"BB:{bb_pos}" if bb_pos != "-" else "-"

            fund_detail = "-"
        except Exception:
            pass

        results.append(SelectionResultItem(
            code=code,
            name=stock_name,
            score=round(score, 2),
            close_price=latest_close,
            pct_chg=round(latest_pct_chg, 2),
            tradable=-10 <= latest_pct_chg <= 10,
            trend_detail=trend_detail,
            momentum_detail=momentum_detail,
            volume_detail=volume_detail,
            vol_detail=vol_detail,
            fund_detail=fund_detail,
            sub_scores=sub_scores,
            completeness=completeness,
        ))

    results.sort(key=lambda x: x.score, reverse=True)
    # 按最低评分阈值过滤
    results = [r for r in results if r.score >= selection_config.min_score_threshold]
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
