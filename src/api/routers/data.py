"""
数据路由：数据下载、股票列表、股票详情、删除、全量列表、WebSocket 实时进度
"""

import asyncio
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from src.api.deps import (
    get_raw_data_path,
    get_processed_data_path,
    download_task_manager,
    parse_stock_codes,
)
from src.api.schemas import (
    DownloadRequest,
    DownloadTaskInfo,
    StockListResponse,
    StockInfo,
    StockDetailResponse,
    StockDeleteResponse,
    FullStockListResponse,
)
from src.core.cache import cache
from src.core.config import config_loader
from src.data.providers.akshare_provider import AKShareProvider
from src.core.logger import get_logger

router = APIRouter(prefix="/api/data", tags=["Data"])
logger = get_logger("API-Data")


@router.get("/stocks", response_model=StockListResponse)
async def list_stocks():
    cache_key = "stock:list"
    cached = cache.get(cache_key)
    if cached:
        return StockListResponse(**cached)

    raw_path = get_raw_data_path()

    if not raw_path.exists():
        return StockListResponse(total=0, total_rows=0, total_size_mb=0.0, stocks=[])

    raw_files = list(raw_path.glob("*.parquet"))
    if not raw_files:
        return StockListResponse(total=0, total_rows=0, total_size_mb=0.0, stocks=[])

    from src.data.providers.akshare_provider import AKShareProvider
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

    stocks = []
    total_rows = 0
    total_size = 0

    for file in raw_files:
        try:
            df = pd.read_parquet(file)

            stock_name = ""
            if "name" in df.columns and not df.empty:
                stock_name = df.iloc[0]["name"]

            if not stock_name:
                pure_code = file.stem.split(".")[0]
                stock_name = AKShareProvider._stock_name_cache.get(pure_code, "")

            rows = len(df)
            total_rows += rows
            size_kb = file.stat().st_size / 1024
            total_size += size_kb

            start_date = str(df["date"].min()) if "date" in df.columns and not df.empty else None
            end_date = str(df["date"].max()) if "date" in df.columns and not df.empty else None

            stocks.append(StockInfo(
                code=file.stem,
                name=stock_name,
                rows=rows,
                start_date=start_date,
                end_date=end_date,
                file_size_kb=round(size_kb, 2),
            ))
        except Exception as e:
            logger.warning(f"Failed to read {file.name}: {e}")

    result = StockListResponse(
        total=len(stocks),
        total_rows=total_rows,
        total_size_mb=round(total_size / 1024, 2),
        stocks=stocks,
    )

    ttl = config_loader.get("cache.ttl.stock_list", 60)
    cache.set(cache_key, result.model_dump(), ttl=ttl)

    return result


@router.get("/stocks/{code}", response_model=StockDetailResponse)
async def get_stock_detail(
    code: str,
    limit: int = Query(100, ge=1, le=10000, description="返回最近N条记录"),
):
    cache_key = f"stock:detail:{code}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return StockDetailResponse(**cached)

    raw_path = get_raw_data_path()

    pure_code = code.split(".")[0] if "." in code else code
    matching_files = list(raw_path.glob(f"{pure_code}*.parquet"))

    if not matching_files:
        raise HTTPException(status_code=404, detail=f"股票数据不存在: {code}")

    file_path = matching_files[0]

    try:
        df = pd.read_parquet(file_path)
        if df.empty:
            raise HTTPException(status_code=404, detail="股票数据为空")

        df["date"] = pd.to_datetime(df["date"])

        stock_name = ""
        if "name" in df.columns:
            stock_name = df.iloc[0].get("name", "")

        if "pct_chg" not in df.columns:
            df["pct_chg"] = ((df["close_price"] - df["close_price"].shift(1)) / df["close_price"].shift(1) * 100).round(2)

        display_df = df.tail(limit)
        data_records = display_df.to_dict(orient="records")

        for record in data_records:
            for k, v in record.items():
                if hasattr(v, "isoformat"):
                    record[k] = v.isoformat()
                elif pd.isna(v):
                    record[k] = None

        latest_close = float(df.iloc[-1]["close_price"]) if not df.empty else None

        result = StockDetailResponse(
            code=file_path.stem,
            name=stock_name,
            rows=len(df),
            start_date=str(df["date"].min().date()) if not df.empty else None,
            end_date=str(df["date"].max().date()) if not df.empty else None,
            latest_close=latest_close,
            data=data_records,
        )

        ttl = config_loader.get("cache.ttl.stock_detail", 300)
        cache.set(cache_key, result.model_dump(), ttl=ttl)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@router.post("/download", response_model=dict)
async def download_data(req: DownloadRequest):
    if req.mode == "full":
        try:
            provider = AKShareProvider()
            codes = provider.get_stock_list()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取全量股票列表失败: {str(e)}")
    elif req.mode == "single":
        if not req.codes:
            raise HTTPException(status_code=400, detail="单股下载模式需要提供 codes")
        codes = parse_stock_codes(req.codes)
    else:
        if not req.codes:
            raise HTTPException(status_code=400, detail="批量下载模式需要提供 codes")
        codes = parse_stock_codes(req.codes)

    if not codes:
        raise HTTPException(status_code=400, detail="没有有效的股票代码")

    task_id = download_task_manager.start_download(
        codes=codes,
        start_date=datetime.combine(req.start_date, datetime.min.time()),
        end_date=datetime.combine(req.end_date, datetime.min.time()),
        adjust=req.adjust,
    )

    cache.delete("stock:list")

    return {"task_id": task_id, "total": len(codes), "message": "下载任务已启动"}


@router.get("/download/{task_id}/status", response_model=DownloadTaskInfo)
async def get_download_status(task_id: str):
    task = download_task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return DownloadTaskInfo(
        task_id=task.task_id,
        total=task.total,
        completed=task.completed,
        failed=task.failed,
        current_code=task.current_code,
        current_provider=task.current_provider,
        is_running=task.is_running,
        progress_pct=round(task.progress_pct, 1),
        eta=task.eta,
        logs=list(task.logs),
    )


@router.post("/download/{task_id}/stop", response_model=dict)
async def stop_download(task_id: str):
    success = download_task_manager.stop_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return {"task_id": task_id, "stopped": True}


@router.websocket("/download/{task_id}/ws")
async def download_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()

    queue = await download_task_manager.subscribe(task_id)
    if queue is None:
        await websocket.send_text('{"error": "任务不存在"}')
        await websocket.close()
        return

    try:
        while True:
            msg = await queue.get()
            if msg is None:
                break
            await websocket.send_text(msg)

            import json
            data = json.loads(msg)
            if not data.get("is_running"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        download_task_manager.unsubscribe(task_id, queue)


@router.delete("/stocks/{code}", response_model=StockDeleteResponse)
async def delete_stock(code: str):
    raw_path = get_raw_data_path()
    pure_code = code.split(".")[0] if "." in code else code
    matching_files = list(raw_path.glob(f"{pure_code}*.parquet"))

    deleted = False
    for f in matching_files:
        f.unlink()
        deleted = True

    if deleted:
        cache.delete("stock:list")
        cache.delete_pattern(f"stock:detail:{pure_code}*")

    return StockDeleteResponse(code=code, deleted=deleted)


@router.get("/stock-list", response_model=FullStockListResponse)
async def get_full_stock_list():
    cache_key = "stock:full_list"
    cached = cache.get(cache_key)
    if cached:
        return FullStockListResponse(**cached)

    try:
        provider = AKShareProvider()
        codes = provider.get_stock_list()
        result = FullStockListResponse(total=len(codes), codes=codes)
        cache.set(cache_key, result.model_dump(), ttl=600)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取全量股票列表失败: {str(e)}")
