from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger
from src.data.providers.akshare_provider import AKShareProvider
from src.data.providers.baostock_provider import BaoStockProvider
from src.data.providers.tushare_provider import TushareProvider


class DataManager:
    
    def __init__(self):
        self.providers = {
            "akshare": AKShareProvider,
            "baostock": BaoStockProvider,
            "tushare": TushareProvider,
        }
        self.provider_order = ["akshare", "baostock", "tushare"]
        self.current_provider_index = 0
        self.logger = get_logger(self.__class__.__name__)
        
        config = config_loader.get("data.storage", {})
        self.base_path = Path(config.get("base_path", "./data"))
        self.compression = config.get("compression", "snappy")
    
    def get_provider(self, provider_name: str | None = None):
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name]()
        
        provider_name = self.provider_order[self.current_provider_index]
        return self.providers[provider_name]()
    
    def switch_provider(self) -> str | None:
        if self.current_provider_index < len(self.provider_order) - 1:
            self.current_provider_index += 1
            return self.provider_order[self.current_provider_index]
        return None
    
    def reset_provider(self) -> None:
        self.current_provider_index = 0
    
    def download_stock(
        self,
        code: str,
        start_date: datetime | date,
        end_date: datetime | date,
        adjust: Literal["none", "qfq", "hfq"] = "qfq",
    ) -> pd.DataFrame:
        if isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        if isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.min.time())
        
        for i, provider_name in enumerate(self.provider_order):
            try:
                provider = self.providers[provider_name]()
                df = provider.download_and_save(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
                if not df.empty:
                    self.current_provider_index = i
                    return df
            except Exception as e:
                self.logger.warning(
                    f"Download failed with {provider_name}",
                    code=code,
                    error=str(e),
                )
                continue
        
        return pd.DataFrame()
    
    def download_batch(
        self,
        codes: list[str],
        start_date: datetime | date,
        end_date: datetime | date,
        adjust: Literal["none", "qfq", "hfq"] = "qfq",
        max_workers: int = 1,
    ) -> dict[str, pd.DataFrame]:
        results = {}
        self.reset_provider()
        
        for code in codes:
            df = self.download_stock(code, start_date, end_date, adjust)
            results[code] = df
        
        return results
    
    def load_stock(self, code: str) -> pd.DataFrame:
        file_path = self.base_path / f"{code}.parquet"
        if not file_path.exists():
            return pd.DataFrame()
        return pd.read_parquet(file_path)
    
    def load_batch(self, codes: list[str]) -> pd.DataFrame:
        all_data = []
        for code in codes:
            df = self.load_stock(code)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)
    
    def list_stocks(self) -> list[str]:
        if not self.base_path.exists():
            return []
        return [f.stem for f in self.base_path.glob("*.parquet")]
    
    def get_stock_info(self, code: str) -> dict | None:
        df = self.load_stock(code)
        if df.empty:
            return None
        
        return {
            "code": code,
            "rows": len(df),
            "start_date": df["date"].min() if "date" in df.columns else None,
            "end_date": df["date"].max() if "date" in df.columns else None,
            "file_size_kb": (self.base_path / f"{code}.parquet").stat().st_size / 1024,
        }
    
    def delete_stock(self, code: str) -> bool:
        file_path = self.base_path / f"{code}.parquet"
        if file_path.exists():
            file_path.unlink()
            self.logger.info(f"Deleted {code}")
            return True
        return False


def create_data_manager() -> DataManager:
    return DataManager()