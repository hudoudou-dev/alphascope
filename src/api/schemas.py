"""
API 请求/响应 Pydantic 模型
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ==================== System ====================

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    timestamp: datetime


class SystemInfoResponse(BaseModel):
    version: str
    python_version: str
    data_base_path: str
    config_path: str


# ==================== Data ====================

class DownloadRequest(BaseModel):
    codes: list[str] = Field(default_factory=list, description="股票代码列表（6位数字，系统自动识别交易所）")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    adjust: Literal["qfq", "hfq", "none"] = Field("qfq", description="复权类型")
    mode: Literal["single", "batch", "full"] = Field("batch", description="下载模式")
    max_workers: int = Field(1, description="并行线程数")


class DownloadTaskInfo(BaseModel):
    task_id: str
    total: int
    completed: int
    failed: int
    current_code: str
    current_provider: str
    is_running: bool
    progress_pct: float
    eta: str
    logs: list[str]


class StockInfo(BaseModel):
    code: str
    name: str
    rows: int
    start_date: str | None
    end_date: str | None
    file_size_kb: float


class StockListResponse(BaseModel):
    total: int
    total_rows: int
    total_size_mb: float
    stocks: list[StockInfo]


class StockDetailResponse(BaseModel):
    code: str
    name: str
    rows: int
    start_date: str | None
    end_date: str | None
    latest_close: float | None
    data: list[dict[str, Any]]


class StockDeleteResponse(BaseModel):
    code: str
    deleted: bool


class FullStockListResponse(BaseModel):
    total: int
    codes: list[str]


# ==================== Strategy ====================

class SelectionConfigResponse(BaseModel):
    market_cap_min: float
    market_cap_max: float
    price_min: float
    price_max: float
    limit_up_min: int
    limit_down_max: int
    limit_stat_period: int
    max_up_threshold: float
    max_down_threshold: float
    initial_cash: float
    max_positions: int
    top_n: int
    min_score_threshold: float
    cooldown_days: int
    max_trades_per_day: int
    # 新5因子权重
    trend_weight: float = 30.0
    momentum_weight: float = 25.0
    volume_weight: float = 20.0
    volatility_weight: float = 15.0
    fundamental_weight: float = 10.0
    # 风控开关
    enable_risk_control: bool = True
    enable_st_filter: bool = True
    enable_limit_filter: bool = True
    # 横截面标准化 / 行情自适应开关
    cross_sectional_enabled: bool = False
    regime_enabled: bool = False


class SelectionConfigUpdate(BaseModel):
    market_cap_min: float | None = None
    market_cap_max: float | None = None
    price_min: float | None = None
    price_max: float | None = None
    limit_up_min: int | None = None
    limit_down_max: int | None = None
    limit_stat_period: int | None = None
    max_up_threshold: float | None = None
    max_down_threshold: float | None = None
    initial_cash: float | None = None
    max_positions: int | None = None
    top_n: int | None = None
    min_score_threshold: float | None = None
    cooldown_days: int | None = None
    max_trades_per_day: int | None = None
    # 新5因子权重
    trend_weight: float | None = None
    momentum_weight: float | None = None
    volume_weight: float | None = None
    volatility_weight: float | None = None
    fundamental_weight: float | None = None
    # 风控开关
    enable_risk_control: bool | None = None
    enable_st_filter: bool | None = None
    enable_limit_filter: bool | None = None
    cross_sectional_enabled: bool | None = None
    regime_enabled: bool | None = None


class ConfigUpdateResponse(BaseModel):
    success: bool
    message: str


# ==================== Selection ====================

class SelectionResultItem(BaseModel):
    code: str
    name: str
    score: float
    close_price: float
    pct_chg: float
    tradable: bool
    # 因子明细
    trend_detail: str = ""
    momentum_detail: str = ""
    volume_detail: str = ""
    vol_detail: str = ""
    fund_detail: str = ""
    # 子策略分项得分（多策略组合模式）
    sub_scores: dict[str, float] = Field(default_factory=dict, description="各子策略分项得分")
    # 数据完整度信息
    completeness: dict[str, dict] = Field(default_factory=dict, description="子策略数据完整度: {策略名: {completeness, missing_factors}}")


class SelectionRunResponse(BaseModel):
    total_scanned: int
    total_selected: int
    avg_score: float
    tradable_count: int
    results: list[SelectionResultItem]


# ==================== Backtest ====================

class BacktestRunRequest(BaseModel):
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    initial_cash: float = Field(1000000, description="初始资金")
    max_positions: int = Field(10, description="最大持仓数")
    stop_loss_pct: float = Field(-8.0, description="止损线(%)")
    take_profit_pct: float = Field(20.0, description="止盈线(%)")
    max_drawdown_limit: int = Field(20, description="最大回撤限制(%)")


class TransactionItem(BaseModel):
    date: str
    code: str
    action: str
    price: float
    shares: int
    amount: float
    commission: float
    profit: float
    total_value: float
    reason: str


class PortfolioStateItem(BaseModel):
    date: str
    capital: float
    positions_value: float
    total_value: float


class BacktestResultResponse(BaseModel):
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_slippage_cost: float
    transactions: list[TransactionItem]
    portfolio_states: list[PortfolioStateItem]


# ==================== Calendar ====================

class TradingDayCheckResponse(BaseModel):
    check_date: str
    is_trading_day: bool


class TradingDayNavResponse(BaseModel):
    check_date: str
    previous_trading_day: str | None
    next_trading_day: str | None
    is_market_open: bool
    latest_closed_trading_day: str | None


class CalendarDownloadRequest(BaseModel):
    start_date: date
    end_date: date
    source: Literal["akshare", "baostock"] = "akshare"


class CalendarDownloadResponse(BaseModel):
    success: bool
    count: int
    start_date: str
    end_date: str
