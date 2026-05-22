from datetime import datetime
from typing import Literal

import baostock as bs
import pandas as pd

from src.data.providers.base_data_provider import BaseDataProvider


class BaoStockProvider(BaseDataProvider):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_name = "baostock"
        self._logged_in = False
    
    def _login(self) -> None:
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != "0":
                raise ConnectionError(f"BaoStock login failed: {lg.error_msg}")
            self._logged_in = True
            self.logger.debug("BaoStock logged in")
    
    def _logout(self) -> None:
        if self._logged_in:
            bs.logout()
            self._logged_in = False
            self.logger.debug("BaoStock logged out")
    
    def __enter__(self):
        self._login()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logout()
    
    def fetch_daily_data(
        self,
        code: str,
        start_date: str | datetime,
        end_date: str | datetime,
        adjust: Literal["none", "qfq", "hfq"] = "qfq",
    ) -> pd.DataFrame:
        self._login()
        
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y-%m-%d")
        
        bs_code = self._to_bs_code(code)
        
        adjust_type_map = {
            "none": "3",
            "qfq": "2",
            "hfq": "1",
        }
        
        adjust_type = adjust_type_map.get(adjust, "2")
        
        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount,turn,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag=adjust_type,
            )
            
            if rs.error_code != "0":
                raise RuntimeError(f"BaoStock query failed: {rs.error_msg}")
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            df = self._normalize_columns(df, code)
            
            return df
            
        except Exception as e:
            self.logger.error(
                "Failed to fetch data from BaoStock",
                code=code,
                error=str(e),
            )
            raise
    
    def _to_bs_code(self, code: str) -> str:
        if "." in code:
            pure_code, exchange = code.split(".")
            exchange = exchange.lower()
        else:
            pure_code = code
            if code.startswith("6"):
                exchange = "sh"
            elif code.startswith(("0", "3")):
                exchange = "sz"
            else:
                exchange = "sh"
        
        return f"{exchange}.{pure_code}"
    
    def _from_bs_code(self, bs_code: str) -> str:
        if "." not in bs_code:
            return self._normalize_code(bs_code)
        
        exchange, pure_code = bs_code.split(".")
        exchange = exchange.upper()
        
        if exchange == "SH":
            return f"{pure_code}.SH"
        elif exchange == "SZ":
            return f"{pure_code}.SZ"
        else:
            return f"{pure_code}.{exchange}"
    
    def _normalize_columns(self, df: pd.DataFrame, code: str) -> pd.DataFrame:
        column_mapping = {
            "date": "date",
            "open": "open_price",
            "high": "high_price",
            "low": "low_price",
            "close": "close_price",
            "volume": "volume",
            "amount": "amount",
            "pctChg": "pct_chg",
            "turn": "turn",
        }
        
        df = df.rename(columns=column_mapping)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        
        for col in ["open_price", "high_price", "low_price", "close_price", "volume", "amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
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
        self._login()
        
        try:
            rs = bs.query_stock_basic()
            
            if rs.error_code != "0":
                raise RuntimeError(f"BaoStock query failed: {rs.error_msg}")
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            stock_list = []
            for _, row in df.iterrows():
                if row["type"] == "1":
                    bs_code = row["code"]
                    normalized_code = self._from_bs_code(bs_code)
                    stock_list.append(normalized_code)
            
            self.logger.info("Fetched stock list", count=len(stock_list))
            return stock_list
            
        except Exception as e:
            self.logger.error("Failed to fetch stock list", error=str(e))
            raise
    
    def get_trade_calendar(
        self,
        start_date: str | datetime,
        end_date: str | datetime,
    ) -> list[str]:
        self._login()
        
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y-%m-%d")
        
        try:
            rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
            
            if rs.error_code != "0":
                raise RuntimeError(f"BaoStock query failed: {rs.error_msg}")
            
            trade_dates = []
            while rs.next():
                row = rs.get_row_data()
                if row[1] == "1":
                    trade_dates.append(row[0])
            
            return trade_dates
            
        except Exception as e:
            self.logger.error("Failed to fetch trade calendar", error=str(e))
            raise
