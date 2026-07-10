import os
from datetime import datetime
from typing import Literal

import akshare as ak
import pandas as pd
import tushare as ts

from src.core.config import config_loader
from src.data.providers.base_data_provider import BaseDataProvider


class TushareProvider(BaseDataProvider):
    
    # 股票名称缓存
    _stock_name_cache: dict[str, str] = {}
    _cache_loaded: bool = False
    
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

            # 合并 daily_basic 基本面/市值列（pe_ttm, pb, total_mv 等）；
            # 这些列供 QualityStrategy 基本面因子与市值区间过滤使用，缺失时优雅跳过。
            df = self._merge_daily_basic(df, code, start_date, end_date)

            # 获取股票名称（使用缓存，避免每次都调用 API）
            pure_code = code.split(".")[0] if "." in code else code
            stock_name = self._get_stock_name_cached(pure_code)
            
            # 添加股票名称字段
            if stock_name:
                df["name"] = stock_name
            
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
    
    def _get_stock_name_cached(self, pure_code: str) -> str:
        """
        获取股票名称（使用缓存）
        
        Args:
            pure_code: 纯股票代码（不带交易所后缀）
        
        Returns:
            str: 股票名称
        """
        # 如果缓存已加载，直接从缓存中获取
        if TushareProvider._cache_loaded and pure_code in TushareProvider._stock_name_cache:
            return TushareProvider._stock_name_cache[pure_code]
        
        # 如果缓存未加载，尝试加载缓存
        if not TushareProvider._cache_loaded:
            try:
                # 使用 akshare 的 stock_info_a_code_name 获取股票代码和名称列表
                df = ak.stock_info_a_code_name()
                
                # 构建缓存
                for _, row in df.iterrows():
                    code = row.get("code", "")
                    name = row.get("name", "")
                    if code and name:
                        TushareProvider._stock_name_cache[code] = name
                
                TushareProvider._cache_loaded = True
                
                # 从缓存中获取
                if pure_code in TushareProvider._stock_name_cache:
                    return TushareProvider._stock_name_cache[pure_code]
            
            except Exception as e:
                self.logger.warning(
                    "Failed to load stock name cache",
                    error=str(e),
                )
        
        # 如果缓存加载失败或找不到，尝试从其他API获取股票名称
        try:
            # 使用 akshare 的 stock_individual_info_em 获取股票信息
            df = ak.stock_individual_info_em(symbol=pure_code)
            if not df.empty:
                # 从DataFrame中获取股票名称
                for _, row in df.iterrows():
                    if row.get("item") == "股票简称":
                        stock_name = row.get("value", "")
                        if stock_name:
                            # 将股票名称添加到缓存
                            TushareProvider._stock_name_cache[pure_code] = stock_name
                            return stock_name
        except Exception as e:
            self.logger.warning(
                "Failed to get stock name from individual info",
                code=pure_code,
                error=str(e),
            )
        
        # 如果所有方法都失败，返回空字符串
        return ""
    
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

    def get_daily_basic_history(
        self, code: str, start_date: str | datetime, end_date: str | datetime
    ) -> pd.DataFrame:
        """一次性拉取某股票区间内的 daily_basic（估值/市值）序列，用于与日线行情合并。"""
        ts_code = self._to_ts_code(code)

        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y%m%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y%m%d")

        try:
            df = self.pro.daily_basic(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields="ts_code,trade_date,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,total_mv,circ_mv",
            )
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={"trade_date": "date"})
            df["date"] = pd.to_datetime(df["date"])
            return df

        except Exception as e:
            self.logger.warning("Failed to fetch daily_basic history", code=code, error=str(e))
            return pd.DataFrame()

    def _merge_daily_basic(
        self,
        df: pd.DataFrame,
        code: str,
        start_date: str | datetime,
        end_date: str | datetime,
    ) -> pd.DataFrame:
        """将 daily_basic 的估值/市值列左连接到日线行情；任何失败均降级为不合并。"""
        if df.empty or "date" not in df.columns:
            return df

        try:
            basic = self.get_daily_basic_history(code, start_date, end_date)
            if basic.empty:
                return df

            keep = ["date", "pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "total_mv", "circ_mv"]
            basic = basic[[c for c in keep if c in basic.columns]]

            merged = df.merge(basic, on="date", how="left")
            self.logger.debug(
                "merged daily_basic fundamentals",
                code=code,
                columns=[c for c in keep if c != "date" and c in basic.columns],
            )
            return merged
        except Exception as e:
            self.logger.warning("merge daily_basic failed", code=code, error=str(e))
            return df
