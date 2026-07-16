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
    
    def calculate_roe(self, net_profit: float, total_equity: float) -> float | None:
        if total_equity <= 0:
            return None
        return net_profit / total_equity
    
    def calculate_debt_to_equity(self, total_debt: float, total_equity: float) -> float | None:
        if total_debt <= 0:
            return 0.0
        if total_equity <= 0:
            return None
        return total_debt / total_equity
    
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
    
    def score_fundamental(
        self,
        pe: float | None,
        pb: float | None,
        roe: float | None,
        debt_to_equity: float | None,
    ) -> float:
        """基本面综合评分（P2-H3: PE上限放宽至100，采用更温和的公式包容成长股）"""
        score = 50.0
        factors = 0
        
        # PE: 上限从50放宽至100，公式从30-PE*0.6改为30-PE*0.3（更温和）
        if pe is not None and 0 < pe < 100:
            pe_score = max(0, 30 - pe * 0.3)
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