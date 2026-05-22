from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import config_loader
from src.core.logger import get_logger
from src.data.schema import DataValidator


class BaseDataProvider(ABC):
    
    def __init__(
        self,
        storage_path: str | Path | None = None,
        compression: str = "snappy",
        retry_times: int = 3,
        retry_delay: float = 1.0,
        timezone: str = "Asia/Shanghai",
    ):
        config = config_loader.data_config
        
        if storage_path is None:
            storage_path = config.get("storage", {}).get("base_path", "./data")
        
        self.storage_path = Path(storage_path)
        self.compression = compression
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self.timezone = timezone
        
        validation_config = config.get("validation", {})
        self.validator = DataValidator(
            check_future_date=validation_config.get("check_future_date", True),
            check_negative_price=validation_config.get("check_negative_price", True),
            check_duplicate_date=validation_config.get("check_duplicate_date", True),
            check_missing_values=validation_config.get("check_missing_values", True),
        )
        
        self.logger = get_logger(self.__class__.__name__)
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def fetch_daily_data(
        self,
        code: str,
        start_date: str | datetime,
        end_date: str | datetime,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_stock_list(self) -> list[str]:
        pass
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def download_and_save(
        self,
        code: str,
        start_date: str | datetime,
        end_date: str | datetime,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        self.logger.info(
            "Starting download",
            code=code,
            start_date=str(start_date),
            end_date=str(end_date),
            adjust=adjust,
        )
        
        try:
            df = self.fetch_daily_data(code, start_date, end_date, adjust)
            
            if df.empty:
                self.logger.warning("Empty data returned", code=code)
                return df
            
            df = self.validator.cast_dtypes(df)
            df = self.validator.validate(df)
            
            self._save_to_parquet(df, code)
            
            self.logger.info(
                "Download completed",
                code=code,
                rows=len(df),
                start_date=str(df["date"].min()),
                end_date=str(df["date"].max()),
            )
            
            return df
            
        except Exception as e:
            self.logger.error(
                "Download failed",
                code=code,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    def incremental_update(
        self,
        code: str,
        end_date: str | datetime,
        lookback_days: int = 30,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        self.logger.info("Starting incremental update", code=code)
        
        existing_data = self._load_from_parquet(code)
        
        if existing_data.empty:
            self.logger.info("No existing data, performing full download", code=code)
            config = config_loader.data_config
            start_date = config.get("update", {}).get("lookback_days", 365)
            start_date = datetime.now() - pd.Timedelta(days=start_date)
            return self.download_and_save(code, start_date, end_date, adjust)
        
        last_date = existing_data["date"].max()
        start_date = last_date + pd.Timedelta(days=1)
        
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        if start_date > end_date:
            self.logger.info(
                "Data already up to date",
                code=code,
                last_date=str(last_date),
            )
            return existing_data
        
        new_data = self.fetch_daily_data(code, start_date, end_date, adjust)
        
        if new_data.empty:
            self.logger.info("No new data available", code=code)
            return existing_data
        
        new_data = self.validator.cast_dtypes(new_data)
        new_data = self.validator.validate(new_data)
        
        combined = pd.concat([existing_data, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=["code", "date"], keep="last")
        combined = combined.sort_values("date").reset_index(drop=True)
        
        self._save_to_parquet(combined, code)
        
        self.logger.info(
            "Incremental update completed",
            code=code,
            new_rows=len(new_data),
            total_rows=len(combined),
        )
        
        return combined
    
    def _save_to_parquet(self, df: pd.DataFrame, code: str) -> None:
        if df.empty:
            return
        
        file_path = self._get_parquet_path(code)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        table = pa.Table.from_pandas(df, preserve_index=False)
        
        pq.write_table(
            table,
            file_path,
            compression=self.compression,
        )
        
        self.logger.debug("Data saved to parquet", file_path=str(file_path))
    
    def _load_from_parquet(self, code: str) -> pd.DataFrame:
        file_path = self._get_parquet_path(code)
        
        if not file_path.exists():
            return pd.DataFrame()
        
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        return df
    
    def _get_parquet_path(self, code: str) -> Path:
        normalized_code = self._normalize_code(code)
        return self.storage_path / f"{normalized_code}.parquet"
    
    def _normalize_code(self, code: str) -> str:
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
    
    def get_available_data(self, code: str) -> pd.DataFrame:
        return self._load_from_parquet(code)
    
    def delete_data(self, code: str) -> None:
        file_path = self._get_parquet_path(code)
        if file_path.exists():
            file_path.unlink()
            self.logger.info("Data deleted", code=code, file_path=str(file_path))
    
    def list_available_codes(self) -> list[str]:
        parquet_files = list(self.storage_path.glob("*.parquet"))
        return [f.stem for f in parquet_files]
