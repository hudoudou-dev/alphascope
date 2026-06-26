from datetime import datetime
from typing import Any, Literal

import pandas as pd

from src.core.logger import get_logger


class FundamentalIndicators:
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def calculate_pe(self, price: float, earnings_per_share: float) -> float | None:
        if earnings_per_share <= 0:
            return None
        return price / earnings_per_share
    
    def calculate_pb(self, price: float, book_value_per_share: float) -> float | None:
        if book_value_per_share <= 0:
            return None
        return price / book_value_per_share
    
    def calculate_ps(self, price: float, revenue_per_share: float) -> float | None:
        if revenue_per_share <= 0:
            return None
        return price / revenue_per_share
    
    def calculate_roe(self, net_profit: float, total_equity: float) -> float | None:
        if total_equity <= 0:
            return None
        return net_profit / total_equity
    
    def calculate_roa(self, net_profit: float, total_assets: float) -> float | None:
        if total_assets <= 0:
            return None
        return net_profit / total_assets
    
    def calculate_gross_margin(self, revenue: float, cost: float) -> float:
        if revenue <= 0:
            return 0.0
        return (revenue - cost) / revenue * 100
    
    def calculate_net_margin(self, net_profit: float, revenue: float) -> float:
        if revenue <= 0:
            return 0.0
        return net_profit / revenue * 100
    
    def calculate_debt_to_equity(self, total_debt: float, total_equity: float) -> float | None:
        if total_equity <= 0:
            return None
        return total_debt / total_equity
    
    def calculate_current_ratio(self, current_assets: float, current_liabilities: float) -> float | None:
        if current_liabilities <= 0:
            return None
        return current_assets / current_liabilities
    
    def calculate_quick_ratio(
        self,
        current_assets: float,
        inventory: float,
        current_liabilities: float,
    ) -> float | None:
        if current_liabilities <= 0:
            return None
        quick_assets = current_assets - inventory
        if quick_assets < 0:
            return None
        return quick_assets / current_liabilities
    
    def calculate_dividend_yield(self, dividend_per_share: float, price: float) -> float | None:
        if price <= 0:
            return None
        return dividend_per_share / price * 100
    
    def calculate_earnings_growth(
        self,
        current_earnings: float,
        previous_earnings: float,
    ) -> float | None:
        if previous_earnings <= 0:
            return None
        return (current_earnings - previous_earnings) / previous_earnings * 100
    
    def calculate_revenue_growth(
        self,
        current_revenue: float,
        previous_revenue: float,
    ) -> float | None:
        if previous_revenue <= 0:
            return None
        return (current_revenue - previous_revenue) / previous_revenue * 100
    
    def add_fundamental_to_dataframe(
        self,
        df: pd.DataFrame,
        fundamental_data: dict[str, dict[str, float]],
    ) -> pd.DataFrame:
        result = df.copy()
        
        for code, fundamentals in fundamental_data.items():
            mask = result["code"] == code
            if not mask.any():
                continue
            
            for key, value in fundamentals.items():
                col_name = f"fundamental_{key}"
                if col_name not in result.columns:
                    result[col_name] = None
                result.loc[mask, col_name] = value
        
        return result
    
    def filter_by_pe(self, df: pd.DataFrame, max_pe: float = 50.0) -> pd.DataFrame:
        if "fundamental_pe" not in df.columns:
            return df
        return df[(df["fundamental_pe"].isna()) | (df["fundamental_pe"] <= max_pe)]
    
    def filter_by_market_cap(
        self,
        df: pd.DataFrame,
        min_market_cap: float = 10_000_000_000.0,
        max_market_cap: float = 500_000_000_000.0,
    ) -> pd.DataFrame:
        if "fundamental_market_cap" not in df.columns:
            return df
        return df[
            (df["fundamental_market_cap"] >= min_market_cap) &
            (df["fundamental_market_cap"] <= max_market_cap)
        ]
    
    def score_fundamental(
        self,
        pe: float | None,
        pb: float | None,
        roe: float | None,
        debt_to_equity: float | None,
    ) -> float:
        score = 50.0
        factors = 0
        
        if pe is not None and 0 < pe < 50:
            pe_score = max(0, 30 - pe * 0.6)
            score += pe_score
            factors += 1
        
        if pb is not None and 0 < pb < 10:
            pb_score = max(0, 20 - pb * 2)
            score += pb_score
            factors += 1
        
        if roe is not None and roe > 0:
            roe_score = min(roe * 2, 20)
            score += roe_score
            factors += 1
        
        if debt_to_equity is not None and debt_to_equity < 2:
            debt_score = max(0, 15 - debt_to_equity * 7.5)
            score += debt_score
            factors += 1
        
        if factors > 0:
            score = score / (1 + 0.1 * factors)
        
        return min(100, max(0, score))