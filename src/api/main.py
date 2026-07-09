"""
AlphaScope FastAPI 应用入口

启动方式：
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

API 文档：
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import system, data, strategy, selection, backtest, calendar
from src.api.deps import download_task_manager
from src.core.cache import cache
from src.core.logger import get_logger

logger = get_logger("App")

app = FastAPI(
    title="AlphaScope API",
    description="A股量化选股与回测平台 - REST API + WebSocket",
    version="3.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(data.router)
app.include_router(strategy.router)
app.include_router(selection.router)
app.include_router(backtest.router)
app.include_router(calendar.router)


@app.on_event("startup")
async def startup_event():
    import asyncio
    download_task_manager.set_loop(asyncio.get_running_loop())
    cache_type = "Redis" if cache.__class__.__name__ == "RedisCache" else "Memory (fallback)"
    logger.info(f"Cache backend: {cache_type}")


@app.get("/")
async def root():
    return {
        "name": "AlphaScope API",
        "version": "3.2.0",
        "cache": cache.__class__.__name__,
        "docs": "/docs",
    }
