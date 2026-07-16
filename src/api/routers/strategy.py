"""
策略路由：选股配置读写、重置
"""

from fastapi import APIRouter

from src.core.cache import cache
from src.core.config import config_loader
from src.strategy.selection_strategy import SelectionConfig
from src.api.schemas import (
    SelectionConfigResponse,
    SelectionConfigUpdate,
    ConfigUpdateResponse,
)

router = APIRouter(prefix="/api/strategy", tags=["Strategy"])

_CACHE_KEY = "strategy:config"

_CONFIG_KEY_MAP = {
    "market_cap_min": "strategy.selection.market_cap_min",
    "market_cap_max": "strategy.selection.market_cap_max",
    "price_min": "strategy.selection.price_min",
    "price_max": "strategy.selection.price_max",
    "limit_up_min": "strategy.selection.limit_up_min",
    "limit_down_max": "strategy.selection.limit_down_max",
    "limit_stat_period": "strategy.selection.limit_stat_period",
    "max_up_threshold": "strategy.selection.max_up_threshold",
    "max_down_threshold": "strategy.selection.max_down_threshold",
    "initial_cash": "strategy.selection.initial_cash",
    "max_positions": "strategy.selection.max_positions",
    "top_n": "strategy.selection.top_n",
    "min_score_threshold": "strategy.selection.min_score_threshold",
    "cooldown_days": "strategy.selection.cooldown_days",
    "max_trades_per_day": "strategy.selection.max_trades_per_day",
    # 4子策略融合权重
    "trend_weight": "strategy.selection.trend_weight",
    "momentum_weight": "strategy.selection.momentum_weight",
    "volume_price_weight": "strategy.selection.volume_price_weight",
    "quality_weight": "strategy.selection.quality_weight",
    # 风控开关
    "enable_risk_control": "strategy.selection.enable_risk_control",
    "enable_st_filter": "strategy.selection.enable_st_filter",
    "enable_limit_filter": "strategy.selection.enable_limit_filter",
    "cross_sectional_enabled": "strategy.selection.cross_sectional_enabled",
    "regime_enabled": "strategy.selection.regime_enabled",
}


@router.get("/config", response_model=SelectionConfigResponse)
async def get_strategy_config():
    cached = cache.get(_CACHE_KEY)
    if cached:
        return SelectionConfigResponse(**cached)

    cfg = SelectionConfig.from_config()
    result = SelectionConfigResponse(**cfg.to_config_dict())
    cache.set(_CACHE_KEY, result.model_dump(), ttl=30)
    return result


@router.put("/config", response_model=ConfigUpdateResponse)
async def update_strategy_config(req: SelectionConfigUpdate):
    updated_keys = []
    for field_name, value in req.model_dump(exclude_none=True).items():
        config_key = _CONFIG_KEY_MAP.get(field_name)
        if config_key and value is not None:
            config_loader.update(config_key, value)
            updated_keys.append(field_name)

    cache.delete(_CACHE_KEY)

    return ConfigUpdateResponse(
        success=True,
        message=f"已更新 {len(updated_keys)} 项配置: {', '.join(updated_keys)}" if updated_keys else "无更新",
    )


@router.post("/config/reset", response_model=ConfigUpdateResponse)
async def reset_strategy_config():
    default_cfg = SelectionConfig()
    for field_name, config_key in _CONFIG_KEY_MAP.items():
        value = getattr(default_cfg, field_name)
        config_loader.update(config_key, value)

    cache.delete(_CACHE_KEY)

    return ConfigUpdateResponse(success=True, message="配置已重置为默认值")
