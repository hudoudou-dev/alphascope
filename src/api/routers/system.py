"""
系统路由：健康检查、系统信息
"""

import sys
from datetime import datetime

from fastapi import APIRouter

from src.api.deps import get_raw_data_path, get_config_path
from src.api.schemas import HealthResponse, SystemInfoResponse

router = APIRouter(prefix="/api/system", tags=["System"])

APP_VERSION = "3.1.0"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        timestamp=datetime.now(),
    )


@router.get("/info", response_model=SystemInfoResponse)
async def system_info():
    return SystemInfoResponse(
        version=APP_VERSION,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        data_base_path=str(get_raw_data_path().parent),
        config_path=str(get_config_path()),
    )
