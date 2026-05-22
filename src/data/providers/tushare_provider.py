import os
from datetime import datetime
from typing import Literal

import pandas as pd
import tushare as ts

from src.core.config import config_loader
from src.data.providers.base_data_provider import BaseDataProvider


class TushareProvider(BaseDataProvider):
    
    def __init__(self, token: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.provider_name = "tushare"
        
        if token is None:
            config = config_loader.data_config
            providers_config = config.get("providers", {}).get("tushare", {})
            token = providers_config.get("token") or os.getenv("TUSHARE_TOKEN")
        
        if not token:
            raise ValueError("Tushare token is required. Set TUSHARE_TOKEN environment variable or pass token parameter.")
        
        ts.set_token(token)
        self.pro = ts.pro_api()
        self.logger.info("Tushare initialized")
    
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
        
        ts_code = self._to_ts_code(code)
        
        try:
            if adjust == "none":
                df = self.pro.daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                )
            else:
                adj_factor = self.pro.adj_factor(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                )
                
                df = self.pro.daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                )
                
                if not df.empty and not adj_factor.empty:
                    df = df.merge(adj_factor[["trade_date", "adj_factor"]], on="trade_date", how="left")
                    df = self._apply_adjust(df, adjust)
            
            if df.empty:
                return pd.DataFrame()
            
            df = self._normalize_columns(df, code)
            
            return df
            
        except Exception as e:
            self.logger.error(
                "Failed to fetch data from Tushare",
                code=code,
                error=str(e),
            )
            raise
    
    def _to_ts_code(self, code: str) -> str:
        if "." in code:
            return code
        
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith("68"):
            return f"{code}.SH"
        elif code.startswith("8") or code.startswith("4"):
            return f"{code}.BJ"
        else:
            return code
    
    def _apply_adjust(self, df: pd.DataFrame, adjust: str) -> pd.DataFrame:
        if "adj_factor" not in df.columns:
            return df
        
        df = df.copy()
        
        if adjust == "qfq":
            last_factor = df["adj_factor"].iloc[0]
            df["adj_factor"] = df["adj_factor"] / last_factor
        elif adjust == "hfq":
            pass
        
        price_cols = ["open", "high", "low", "close", "pre_close"]
        for col in price_cols:
            if col in df.columns:
                df[col] = df[col] * df["adj_factor"]
        
        return df
    
    def _normalize_columns(self, df: pd.DataFrame, code: str) -> pd.DataFrame:
        column_mapping = {
            "trade_date": "date",
            "open": "open_price",
            "high": "high_price",
            "low": "low_price",
            "close": "close_price",
            "vol": "volume",
            "amount": "amount",
            "pct_chg": "pct_chg",
            "turnover_rate": "turn",
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
        
        df = df.sort_values("date").reset_index(drop=True)
        
        return df
    
    def get_stock_list(self) -> list[str]:
        try:
            df = self.pro.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,list_date")
            
            stock_list = []
            for _, row in df.iterrows():
                ts_code = row["ts_code"]
                normalized_code = self._normalize_code(ts_code)
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
        exchange: str = "SSE",
    ) -> list[str]:
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y%m%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y%m%d")
        
        try:
            df = self.pro.trade_cal(
                exchange=exchange,
                start_date=start_date,
                end_date=end_date,
                is_open="1",
            )
            
            trade_dates = df["cal_date"].tolist()
            return trade_dates
            
        except Exception as e:
            self.logger.error("Failed to fetch trade calendar", error=str(e))
            raise
    
    def get_daily_basic(self, code: str, date: str | datetime) -> dict:
        ts_code = self._to_ts_code(code)
        
        if isinstance(date, datetime):
            date = date.strftime("%Y%m%d")
        
        try:
            df = self.pro.daily_basic(
                ts_code=ts_code,
                trade_date=date,
                fields="ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,total_mv,circ_mv",
            )
            
            if df.empty:
                return {}
            
            row = df.iloc[0]
            return row.to_dict()
            
        except Exception as e:
            self.logger.error("Failed to fetch daily basic", code=code, error=str(e))
            raise
