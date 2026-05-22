from datetime import datetime, date, time
from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import config_loader
from src.core.logger import get_logger


class TradingCalendarService:
    
    MARKET_OPEN_TIME = time(9, 30)
    MARKET_CLOSE_TIME = time(15, 0)
    LUNCH_BREAK_START = time(11, 30)
    LUNCH_BREAK_END = time(13, 0)
    
    def __init__(
        self,
        calendar_path: str | Path | None = None,
        timezone: str = "Asia/Shanghai",
    ):
        config = config_loader.data_config
        
        if calendar_path is None:
            base_path = config.get("storage", {}).get("base_path", "./data")
            calendar_path = Path(base_path) / "calendar" / "trading_days.parquet"
        
        self.calendar_path = Path(calendar_path)
        self.timezone = timezone
        self.logger = get_logger(self.__class__.__name__)
        
        self.calendar_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._trading_days: pd.DataFrame | None = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def download_trading_days(
        self,
        start_date: str | date | datetime,
        end_date: str | date | datetime,
        source: Literal["akshare", "baostock"] = "akshare",
    ) -> pd.DataFrame:
        self.logger.info(
            "Starting download trading days",
            start_date=str(start_date),
            end_date=str(end_date),
            source=source,
        )
        
        if isinstance(start_date, (date, datetime)):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, (date, datetime)):
            end_date = end_date.strftime("%Y-%m-%d")
        
        try:
            if source == "akshare":
                trading_days = self._download_from_akshare(start_date, end_date)
            elif source == "baostock":
                trading_days = self._download_from_baostock(start_date, end_date)
            else:
                raise ValueError(f"Unsupported source: {source}")
            
            trading_days = self._validate_trading_days(trading_days)
            
            self._save_to_parquet(trading_days)
            
            self.logger.info(
                "Download completed",
                count=len(trading_days),
                start_date=str(trading_days["date"].min()),
                end_date=str(trading_days["date"].max()),
            )
            
            return trading_days
            
        except Exception as e:
            self.logger.error(
                "Download failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    def _download_from_akshare(self, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            import akshare as ak
            
            df = ak.tool_trade_date_hist_sina()
            
            df.columns = ["date"]
            df["date"] = pd.to_datetime(df["date"])
            
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
            
            df["is_trading_day"] = True
            df["exchange"] = "SSE"
            
            return df.sort_values("date").reset_index(drop=True)
            
        except Exception as e:
            self.logger.error("Failed to download from AKShare", error=str(e))
            raise
    
    def _download_from_baostock(self, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            import baostock as bs
            
            lg = bs.login()
            if lg.error_code != "0":
                raise ConnectionError(f"BaoStock login failed: {lg.error_msg}")
            
            rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
            
            if rs.error_code != "0":
                raise RuntimeError(f"BaoStock query failed: {rs.error_msg}")
            
            data_list = []
            while rs.next():
                row = rs.get_row_data()
                if row[1] == "1":
                    data_list.append({
                        "date": row[0],
                        "is_trading_day": True,
                        "exchange": "SSE"
                    })
            
            bs.logout()
            
            df = pd.DataFrame(data_list)
            df["date"] = pd.to_datetime(df["date"])
            
            return df.sort_values("date").reset_index(drop=True)
            
        except Exception as e:
            self.logger.error("Failed to download from BaoStock", error=str(e))
            raise
    
    def _validate_trading_days(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise ValueError("Trading days DataFrame is empty")
        
        required_fields = ["date", "is_trading_day"]
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        if df["date"].isna().any():
            raise ValueError("Date field contains missing values")
        
        now = datetime.now()
        future_dates = df["date"] > now
        if future_dates.any():
            self.logger.warning(
                "Found future dates, removing them",
                count=future_dates.sum(),
            )
            df = df[~future_dates]
        
        duplicates = df.duplicated(subset=["date"])
        if duplicates.any():
            self.logger.warning(
                "Found duplicate dates, removing them",
                count=duplicates.sum(),
            )
            df = df.drop_duplicates(subset=["date"], keep="last")
        
        return df.sort_values("date").reset_index(drop=True)
    
    def _save_to_parquet(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        
        table = pa.Table.from_pandas(df, preserve_index=False)
        
        pq.write_table(
            table,
            self.calendar_path,
            compression="snappy",
        )
        
        self.logger.debug("Trading days saved to parquet", file_path=str(self.calendar_path))
    
    def _load_from_parquet(self) -> pd.DataFrame:
        if not self.calendar_path.exists():
            self.logger.warning("Trading days file not found", file_path=str(self.calendar_path))
            return pd.DataFrame()
        
        table = pq.read_table(self.calendar_path)
        df = table.to_pandas()
        
        return df
    
    def load_trading_days(self) -> pd.DataFrame:
        if self._trading_days is None:
            self._trading_days = self._load_from_parquet()
        
        return self._trading_days
    
    def update_trading_days(self, end_date: str | date | datetime) -> pd.DataFrame:
        self.logger.info("Starting incremental update", end_date=str(end_date))
        
        existing_data = self.load_trading_days()
        
        if existing_data.empty:
            self.logger.info("No existing data, performing full download")
            start_date = "1990-12-19"
            return self.download_trading_days(start_date, end_date)
        
        last_date = existing_data["date"].max()
        start_date = last_date + pd.Timedelta(days=1)
        
        if isinstance(end_date, (date, datetime)):
            end_date = end_date.strftime("%Y-%m-%d")
        
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        if start_date_str > end_date:
            self.logger.info(
                "Trading days already up to date",
                last_date=str(last_date),
            )
            return existing_data
        
        new_data = self.download_trading_days(start_date_str, end_date)
        
        if new_data.empty:
            self.logger.info("No new trading days available")
            return existing_data
        
        combined = pd.concat([existing_data, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date"], keep="last")
        combined = combined.sort_values("date").reset_index(drop=True)
        
        self._save_to_parquet(combined)
        self._trading_days = combined
        
        self.logger.info(
            "Incremental update completed",
            new_count=len(new_data),
            total_count=len(combined),
        )
        
        return combined
    
    def is_trading_day(self, check_date: str | date | datetime) -> bool:
        trading_days = self.load_trading_days()
        
        if trading_days.empty:
            raise ValueError("Trading days data not loaded. Please download first.")
        
        if isinstance(check_date, str):
            check_date = pd.to_datetime(check_date).date()
        elif isinstance(check_date, datetime):
            check_date = check_date.date()
        
        check_dt = pd.to_datetime(check_date)
        
        return check_dt in trading_days["date"].values
    
    def previous_trading_day(self, check_date: str | date | datetime) -> date:
        trading_days = self.load_trading_days()
        
        if trading_days.empty:
            raise ValueError("Trading days data not loaded. Please download first.")
        
        if isinstance(check_date, str):
            check_date = pd.to_datetime(check_date).date()
        elif isinstance(check_date, datetime):
            check_date = check_date.date()
        
        check_dt = pd.to_datetime(check_date)
        
        earlier_days = trading_days[trading_days["date"] < check_dt]
        
        if earlier_days.empty:
            raise ValueError(f"No trading day before {check_date}")
        
        return earlier_days["date"].max().date()
    
    def next_trading_day(self, check_date: str | date | datetime) -> date:
        trading_days = self.load_trading_days()
        
        if trading_days.empty:
            raise ValueError("Trading days data not loaded. Please download first.")
        
        if isinstance(check_date, str):
            check_date = pd.to_datetime(check_date).date()
        elif isinstance(check_date, datetime):
            check_date = check_date.date()
        
        check_dt = pd.to_datetime(check_date)
        
        later_days = trading_days[trading_days["date"] > check_dt]
        
        if later_days.empty:
            raise ValueError(f"No trading day after {check_date}")
        
        return later_days["date"].min().date()
    
    def get_trading_days(
        self,
        start_date: str | date | datetime,
        end_date: str | date | datetime,
    ) -> list[date]:
        trading_days = self.load_trading_days()
        
        if trading_days.empty:
            raise ValueError("Trading days data not loaded. Please download first.")
        
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        elif isinstance(start_date, (date, datetime)):
            start_date = pd.to_datetime(start_date)
        
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        elif isinstance(end_date, (date, datetime)):
            end_date = pd.to_datetime(end_date)
        
        filtered = trading_days[
            (trading_days["date"] >= start_date) &
            (trading_days["date"] <= end_date)
        ]
        
        return [d.date() for d in filtered["date"]]
    
    def is_market_open(self, check_time: datetime | None = None) -> bool:
        if check_time is None:
            check_time = datetime.now()
        
        if not self.is_trading_day(check_time.date()):
            return False
        
        current_time = check_time.time()
        
        morning_session = self.MARKET_OPEN_TIME <= current_time <= self.LUNCH_BREAK_START
        afternoon_session = self.LUNCH_BREAK_END <= current_time <= self.MARKET_CLOSE_TIME
        
        return morning_session or afternoon_session
    
    def is_market_closed(self, check_time: datetime | None = None) -> bool:
        return not self.is_market_open(check_time)
    
    def latest_closed_trading_day(self, check_time: datetime | None = None) -> date:
        if check_time is None:
            check_time = datetime.now()
        
        if self.is_trading_day(check_time.date()) and check_time.time() >= self.MARKET_CLOSE_TIME:
            return check_time.date()
        
        return self.previous_trading_day(check_time.date())
    
    def get_trading_days_count(
        self,
        start_date: str | date | datetime,
        end_date: str | date | datetime,
    ) -> int:
        trading_days = self.get_trading_days(start_date, end_date)
        return len(trading_days)
    
    def get_all_trading_days(self) -> list[date]:
        trading_days = self.load_trading_days()
        
        if trading_days.empty:
            raise ValueError("Trading days data not loaded. Please download first.")
        
        return [d.date() for d in trading_days["date"]]