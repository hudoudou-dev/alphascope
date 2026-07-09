"""
交易日历路由
"""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    TradingDayCheckResponse,
    TradingDayNavResponse,
    CalendarDownloadRequest,
    CalendarDownloadResponse,
)
from src.calendar.trading_calendar import TradingCalendarService
from src.core.logger import get_logger

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])
logger = get_logger("API-Calendar")


def _get_calendar():
    try:
        return TradingCalendarService()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"日历服务初始化失败: {str(e)}")


@router.get("/check", response_model=TradingDayCheckResponse)
async def check_trading_day(check_date: date):
    cal = _get_calendar()
    try:
        is_td = cal.is_trading_day(check_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return TradingDayCheckResponse(
        check_date=check_date.isoformat(),
        is_trading_day=is_td,
    )


@router.get("/nav", response_model=TradingDayNavResponse)
async def trading_day_nav(check_date: date):
    cal = _get_calendar()
    try:
        prev = cal.previous_trading_day(check_date)
    except (ValueError, Exception):
        prev = None

    try:
        nxt = cal.next_trading_day(check_date)
    except (ValueError, Exception):
        nxt = None

    try:
        is_open = cal.is_market_open(datetime.combine(check_date, datetime.min.time()))
    except (ValueError, Exception):
        is_open = False

    try:
        latest_closed = cal.latest_closed_trading_day(datetime.combine(check_date, datetime.min.time()))
        latest_closed_str = latest_closed.isoformat() if latest_closed else None
    except (ValueError, Exception):
        latest_closed_str = None

    return TradingDayNavResponse(
        check_date=check_date.isoformat(),
        previous_trading_day=prev.isoformat() if prev else None,
        next_trading_day=nxt.isoformat() if nxt else None,
        is_market_open=is_open,
        latest_closed_trading_day=latest_closed_str,
    )


@router.get("/days", response_model=list[str])
async def get_trading_days(start_date: date, end_date: date):
    cal = _get_calendar()
    try:
        days = cal.get_trading_days(start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return [d.isoformat() for d in days]


@router.get("/count", response_model=dict)
async def count_trading_days(start_date: date, end_date: date):
    cal = _get_calendar()
    try:
        count = cal.get_trading_days_count(start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "count": count}


@router.post("/download", response_model=CalendarDownloadResponse)
async def download_trading_days(req: CalendarDownloadRequest):
    cal = _get_calendar()
    try:
        df = cal.download_trading_days(req.start_date, req.end_date, source=req.source)
        return CalendarDownloadResponse(
            success=True,
            count=len(df),
            start_date=str(df["date"].min().date()) if not df.empty else "",
            end_date=str(df["date"].max().date()) if not df.empty else "",
        )
    except Exception as e:
        return CalendarDownloadResponse(
            success=False,
            count=0,
            start_date=req.start_date.isoformat(),
            end_date=req.end_date.isoformat(),
        )
