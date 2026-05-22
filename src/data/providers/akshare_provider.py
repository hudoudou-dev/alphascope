from datetime import datetime
from typing import Literal

import akshare as ak
import pandas as pd

from src.data.providers.base_data_provider import BaseDataProvider


class AKShareProvider(BaseDataProvider):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_name = "akshare"
    
    def fetch_daily_data(
        self,
        code: str,
        start_date: str | datetime,
        end_date: str | datetime,
        adjust: Literal["none", "qfq", "hfq"] = "qfq",
    ) -> pd.DataFrame:
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y%m%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y%m%d")
        
        pure_code = code.split(".")[0] if "." in code else code
        
        adjust_map = {
            "none": "",
            "qfq": "qfq",
            "hfq": "hfq",
        }
        
        adjust_param = adjust_map.get(adjust, "qfq")
        
        try:
            if adjust_param:
                df = ak.stock_zh_a_hist(
                    symbol=pure_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust_param,
                )
            else:
                df = ak.stock_zh_a_hist(
                    symbol=pure_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                )
            
            if df.empty:
                return pd.DataFrame()
            
            df = self._normalize_columns(df, code)
            
            return df
            
        except Exception as e:
            self.logger.error(
                "Failed to fetch data from AKShare",
                code=code,
                error=str(e),
            )
            raise
    
    def _normalize_columns(self, df: pd.DataFrame, code: str) -> pd.DataFrame:
        column_mapping = {
            "日期": "date",
            "开盘": "open_price",
            "收盘": "close_price",
            "最高": "high_price",
            "最低": "low_price",
            "成交量": "volume",
            "成交额": "amount",
            "涨跌幅": "pct_chg",
            "换手率": "turn",
        }
        
        df = df.rename(columns=column_mapping)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        
        if "code" not in df.columns:
            df["code"] = self._normalize_code(code)
        
        required_fields = [
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "amount",
            "code",
        ]
        
        available_fields = [f for f in required_fields if f in df.columns]
        df = df[available_fields + [f for f in df.columns if f not in required_fields]]
        
        return df
    
    def get_stock_list(self) -> list[str]:
        try:
            df = ak.stock_info_a_code_name()
            
            stock_list = []
            for _, row in df.iterrows():
                code = row["code"]
                normalized_code = self._normalize_code(code)
                stock_list.append(normalized_code)
            
            self.logger.info("Fetched stock list", count=len(stock_list))
            return stock_list
            
        except Exception as e:
            self.logger.error("Failed to fetch stock list", error=str(e))
            raise
    
    def get_realtime_data(self, code: str) -> dict:
        pure_code = code.split(".")[0] if "." in code else code
        
        try:
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df["代码"] == pure_code]
            
            if stock_data.empty:
                return {}
            
            row = stock_data.iloc[0]
            return {
                "code": self._normalize_code(code),
                "name": row.get("名称", ""),
                "price": float(row.get("最新价", 0)),
                "change_pct": float(row.get("涨跌幅", 0)),
                "volume": float(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
            }
            
        except Exception as e:
            self.logger.error("Failed to fetch realtime data", code=code, error=str(e))
            raise
