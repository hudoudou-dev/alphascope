from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.core.logger import get_logger


@dataclass
class RiskControlResult:
    allowed: bool
    reason: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class RiskControlConfig:
    enable_st_filter: bool = True
    enable_limit_filter: bool = True
    enable_concentration_filter: bool = True
    max_position_pct: float = 30.0
    max_sector_exposure: float = 40.0
    st_list: list[str] = field(default_factory=list)


class RiskControl:
    
    def __init__(self, config: RiskControlConfig | None = None):
        self.config = config or RiskControlConfig()
        self.logger = get_logger(self.__class__.__name__)
    
    def check_buy(self, code: str, price: float, pct_chg: float | None = None) -> RiskControlResult:
        if self.config.enable_limit_filter and pct_chg is not None:
            if pct_chg >= 9.5:
                return RiskControlResult(
                    allowed=False,
                    reason="涨停股票不可买入",
                    details={"code": code, "pct_chg": pct_chg},
                )
        
        if self.config.enable_st_filter and code in self.config.st_list:
            return RiskControlResult(
                allowed=False,
                reason="ST股票不可买入",
                details={"code": code},
            )
        
        return RiskControlResult(allowed=True)
    
    def check_sell(self, code: str, price: float, pct_chg: float | None = None) -> RiskControlResult:
        if self.config.enable_limit_filter and pct_chg is not None:
            if pct_chg <= -9.5:
                return RiskControlResult(
                    allowed=False,
                    reason="跌停股票不可卖出",
                    details={"code": code, "pct_chg": pct_chg},
                )
        
        return RiskControlResult(allowed=True)
    
    def check_position_limit(
        self,
        code: str,
        current_position_value: float,
        total_portfolio_value: float,
    ) -> RiskControlResult:
        if not self.config.enable_concentration_filter:
            return RiskControlResult(allowed=True)
        
        if total_portfolio_value <= 0:
            return RiskControlResult(allowed=True)
        
        position_pct = (current_position_value / total_portfolio_value) * 100
        
        if position_pct > self.config.max_position_pct:
            return RiskControlResult(
                allowed=False,
                reason=f"单只股票持仓超过限制 ({position_pct:.1f}% > {self.config.max_position_pct}%)",
                details={
                    "code": code,
                    "position_pct": position_pct,
                    "limit": self.config.max_position_pct,
                },
            )
        
        return RiskControlResult(allowed=True)
    
    def check_sector_concentration(
        self,
        sector: str,
        sector_value: float,
        total_portfolio_value: float,
    ) -> RiskControlResult:
        if not self.config.enable_concentration_filter:
            return RiskControlResult(allowed=True)
        
        if total_portfolio_value <= 0:
            return RiskControlResult(allowed=True)
        
        sector_pct = (sector_value / total_portfolio_value) * 100
        
        if sector_pct > self.config.max_sector_exposure:
            return RiskControlResult(
                allowed=False,
                reason=f"行业集中度超过限制 ({sector_pct:.1f}% > {self.config.max_sector_exposure}%)",
                details={
                    "sector": sector,
                    "sector_pct": sector_pct,
                    "limit": self.config.max_sector_exposure,
                },
            )
        
        return RiskControlResult(allowed=True)
    
    def update_st_list(self, st_codes: list[str]) -> None:
        self.config.st_list = st_codes
        self.logger.info(f"ST list updated with {len(st_codes)} stocks")
    
    def add_st(self, code: str) -> None:
        if code not in self.config.st_list:
            self.config.st_list.append(code)
    
    def remove_st(self, code: str) -> None:
        if code in self.config.st_list:
            self.config.st_list.remove(code)


class MarketFilter:
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._limit_up_codes: set[str] = set()
        self._limit_down_codes: set[str] = set()
        self._st_codes: set[str] = set()
    
    def update_market_status(self, df: pd.DataFrame) -> None:
        if df.empty or "pct_chg" not in df.columns or "code" not in df.columns:
            return
        
        self._limit_up_codes = set(df[df["pct_chg"] >= 9.5]["code"].unique())
        self._limit_down_codes = set(df[df["pct_chg"] <= -9.5]["code"].unique())
        
        self.logger.debug(
            f"Market status updated: {len(self._limit_up_codes)} limit up, "
            f"{len(self._limit_down_codes)} limit down"
        )
    
    def set_st_codes(self, codes: list[str]) -> None:
        self._st_codes = set(codes)
    
    def is_limit_up(self, code: str) -> bool:
        return code in self._limit_up_codes
    
    def is_limit_down(self, code: str) -> bool:
        return code in self._limit_down_codes
    
    def is_st(self, code: str) -> bool:
        return code in self._st_codes
    
    def can_buy(self, code: str) -> tuple[bool, str]:
        if self.is_limit_up(code):
            return False, "涨停"
        if self.is_st(code):
            return False, "ST"
        return True, ""
    
    def can_sell(self, code: str) -> tuple[bool, str]:
        if self.is_limit_down(code):
            return False, "跌停"
        return True, ""