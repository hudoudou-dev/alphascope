"""
数据提供者基类模块

本模块定义了数据提供者的抽象基类，提供统一的数据下载、验证、存储接口。
所有数据提供者（AKShare、BaoStock、Tushare）都继承自此类。

主要功能：
- 数据下载（fetch_daily_data）
- 数据验证（validate）
- 数据存储（save_to_parquet）
- 数据加载（load_from_parquet）
- 增量更新（incremental_update）

存储结构：
- ./data/ - 原始下载的数据
- ./data/processed/ - 预处理后的数据

使用示例：
    from src.data.providers.akshare_provider import AKShareProvider
    
    # 初始化
    provider = AKShareProvider(storage_path="./data")
    
    # 下载数据
    df = provider.download_and_save(
        code="600000.SH",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31)
    )
"""

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
    """
    数据提供者抽象基类
    
    定义了数据提供者的标准接口，包括数据下载、验证、存储等功能。
    
    Attributes:
        storage_path (Path): 原始数据存储路径（./data/）
        processed_path (Path): 预处理数据存储路径（./data/processed/）
        validator (DataValidator): 数据验证器
        logger: 日志记录器
        compression (str): 压缩算法
        retry_times (int): 重试次数
        retry_delay (float): 重试延迟（秒）
    
    Example:
        >>> class MyProvider(BaseDataProvider):
        ...     def fetch_daily_data(self, code, start_date, end_date):
        ...         # 实现数据下载逻辑
        ...         return df
    """
    
    def __init__(
        self,
        storage_path: str | Path | None = None,
        compression: str = "snappy",
        retry_times: int = 3,
        retry_delay: float = 1.0,
        timezone: str = "Asia/Shanghai",
    ):
        """
        初始化数据提供者
        
        Args:
            storage_path: 数据存储路径，默认为 ./data
            compression: 压缩算法，默认为 snappy
            retry_times: 重试次数，默认为 3
            retry_delay: 重试延迟（秒），默认为 1.0
            timezone: 时区，默认为 Asia/Shanghai
        """
        config = config_loader.data_config
        
        if storage_path is None:
            storage_path = config.get("storage", {}).get("base_path", "./data")
        
        self.storage_path = Path(storage_path)
        self.processed_path = self.storage_path / "processed"
        
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
        self.processed_path.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def fetch_daily_data(
        self,
        code: str,
        start_date: str | datetime,
        end_date: str | datetime,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """
        下载股票数据（抽象方法）
        
        子类必须实现此方法，从数据源下载股票数据
        
        Args:
            code: 股票代码，格式为 XXXXXX.EXCHANGE（如 600000.SH）
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型，默认为前复权
        
        Returns:
            pd.DataFrame: 股票数据
        
        Raises:
            ValueError: 参数无效
            ConnectionError: 网络连接失败
        """
        pass
    
    @abstractmethod
    def get_stock_list(self) -> list[str]:
        """
        获取股票列表（抽象方法）
        
        子类必须实现此方法，返回股票代码列表
        
        Returns:
            list[str]: 股票代码列表
        """
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
        """
        下载数据并保存到原始数据目录
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
        
        Returns:
            pd.DataFrame: 下载的数据
        
        Note:
            数据保存在 ./data/{code}.parquet
        """
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
            
            self._save_to_parquet(df, code, processed=False)
            
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
    
    def save_processed_data(self, df: pd.DataFrame, code: str) -> None:
        """
        保存预处理后的数据
        
        Args:
            df: 预处理后的数据
            code: 股票代码
        
        Note:
            数据保存在 ./data/processed/{code}.parquet
        """
        if df.empty:
            self.logger.warning("Cannot save empty DataFrame", code=code)
            return
        
        self._save_to_parquet(df, code, processed=True)
        
        self.logger.info(
            "Processed data saved",
            code=code,
            rows=len(df),
        )
    
    def load_raw_data(self, code: str) -> pd.DataFrame:
        """
        加载原始数据
        
        Args:
            code: 股票代码
        
        Returns:
            pd.DataFrame: 原始数据
        """
        return self._load_from_parquet(code, processed=False)
    
    def load_processed_data(self, code: str) -> pd.DataFrame:
        """
        加载预处理后的数据
        
        Args:
            code: 股票代码
        
        Returns:
            pd.DataFrame: 预处理后的数据
        """
        return self._load_from_parquet(code, processed=True)
    
    def incremental_update(
        self,
        code: str,
        end_date: str | datetime,
        lookback_days: int = 30,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """
        增量更新数据
        
        Args:
            code: 股票代码
            end_date: 结束日期
            lookback_days: 回溯天数
            adjust: 复权类型
        
        Returns:
            pd.DataFrame: 更新后的数据
        """
        self.logger.info("Starting incremental update", code=code)
        
        existing_data = self._load_from_parquet(code, processed=False)
        
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
        
        self._save_to_parquet(combined, code, processed=False)
        
        self.logger.info(
            "Incremental update completed",
            code=code,
            new_rows=len(new_data),
            total_rows=len(combined),
        )
        
        return combined
    
    def _save_to_parquet(
        self,
        df: pd.DataFrame,
        code: str,
        processed: bool = False,
    ) -> None:
        """
        保存数据到 Parquet 文件
        
        Args:
            df: 待保存的数据
            code: 股票代码
            processed: 是否为预处理数据
        """
        if df.empty:
            return
        
        file_path = self._get_parquet_path(code, processed=processed)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        table = pa.Table.from_pandas(df, preserve_index=False)
        
        pq.write_table(
            table,
            file_path,
            compression=self.compression,
        )
        
        self.logger.debug(
            "Data saved to parquet",
            file_path=str(file_path),
            processed=processed,
        )
    
    def _load_from_parquet(
        self,
        code: str,
        processed: bool = False,
    ) -> pd.DataFrame:
        """
        从 Parquet 文件加载数据
        
        Args:
            code: 股票代码
            processed: 是否为预处理数据
        
        Returns:
            pd.DataFrame: 加载的数据
        """
        file_path = self._get_parquet_path(code, processed=processed)
        
        if not file_path.exists():
            return pd.DataFrame()
        
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        return df
    
    def _get_parquet_path(self, code: str, processed: bool = False) -> Path:
        """
        获取 Parquet 文件路径
        
        Args:
            code: 股票代码
            processed: 是否为预处理数据
        
        Returns:
            Path: 文件路径
        
        Note:
            - 原始数据: ./data/{code}.parquet
            - 预处理数据: ./data/processed/{code}.parquet
        """
        normalized_code = self._normalize_code(code)
        
        if processed:
            return self.processed_path / f"{normalized_code}.parquet"
        else:
            return self.storage_path / f"{normalized_code}.parquet"
    
    def _normalize_code(self, code: str) -> str:
        """
        标准化股票代码
        
        Args:
            code: 原始股票代码
        
        Returns:
            str: 标准化后的股票代码（XXXXXX.EXCHANGE）
        """
        code = code.upper().strip()
        
        if "." in code:
            return code
        
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith(("68", "8")):
            return f"{code}.SH"
        else:
            return code
    
    def list_available_codes(self, processed: bool = False) -> list[str]:
        """
        列出可用的股票代码
        
        Args:
            processed: 是否为预处理数据
        
        Returns:
            list[str]: 股票代码列表
        """
        base_path = self.processed_path if processed else self.storage_path
        parquet_files = list(base_path.glob("*.parquet"))
        
        return [file.stem for file in parquet_files]
    
    def delete_data(self, code: str, processed: bool = False) -> bool:
        """
        删除数据文件
        
        Args:
            code: 股票代码
            processed: 是否为预处理数据
        
        Returns:
            bool: 是否成功删除
        """
        file_path = self._get_parquet_path(code, processed=processed)
        
        if file_path.exists():
            file_path.unlink()
            self.logger.info("Data deleted", code=code, processed=processed)
            return True
        
        return False
    
    def get_available_data(self, code: str) -> pd.DataFrame:
        """
        获取可用数据（优先返回预处理数据）
        
        Args:
            code: 股票代码
        
        Returns:
            pd.DataFrame: 数据（优先预处理数据，否则原始数据）
        """
        processed_data = self.load_processed_data(code)
        
        if not processed_data.empty:
            return processed_data
        
        return self.load_raw_data(code)