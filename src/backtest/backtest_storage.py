from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest.backtest_engine import BacktestResult
from src.core.config import config_loader
from src.core.logger import get_logger


@dataclass
class BacktestRecord:
    id: str
    created_at: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_cash: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_slippage_cost: float
    config: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_cash": self.initial_cash,
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_slippage_cost": self.total_slippage_cost,
            "config": self.config,
        }


class BacktestStorage:
    
    def __init__(self, storage_path: str | Path | None = None):
        if storage_path is None:
            storage_path = Path(config_loader.get("backtest.storage_path", "./logs/backtest_history"))
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.records_file = self.storage_path / "records.parquet"
        self.logger = get_logger(self.__class__.__name__)
    
    def save(self, record: BacktestRecord) -> str:
        df = self._load_records()
        
        record_dict = record.to_dict()
        if "config" in record_dict and not record_dict["config"]:
            record_dict["config"] = {"_empty": True}
        new_df = pd.DataFrame([record_dict])
        
        if df.empty:
            df = new_df
        else:
            df = pd.concat([df, new_df], ignore_index=True)
        
        df.to_parquet(self.records_file, compression="snappy", index=False)
        self.logger.info(f"Saved backtest record: {record.id}")
        
        return record.id
    
    def save_from_result(
        self,
        result: BacktestResult,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_cash: float,
        config: dict[str, Any],
    ) -> str:
        from datetime import datetime
        import uuid
        
        record_id = str(uuid.uuid4())[:8]
        
        record = BacktestRecord(
            id=record_id,
            created_at=datetime.now().isoformat(),
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            total_return=result.total_return,
            annual_return=result.annual_return,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=result.sharpe_ratio,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            total_slippage_cost=result.total_slippage_cost,
            config=config,
        )
        
        return self.save(record)
    
    def _load_records(self) -> pd.DataFrame:
        if not self.records_file.exists():
            return pd.DataFrame()
        return pd.read_parquet(self.records_file)
    
    def load_all(self) -> pd.DataFrame:
        return self._load_records()
    
    def load(self, record_id: str) -> BacktestRecord | None:
        df = self._load_records()
        if df.empty:
            return None
        
        filtered = df[df["id"] == record_id]
        if filtered.empty:
            return None
        
        row = filtered.iloc[0]
        return BacktestRecord(**row.to_dict())
    
    def load_recent(self, limit: int = 10) -> pd.DataFrame:
        df = self._load_records()
        if df.empty:
            return pd.DataFrame()
        return df.sort_values("created_at", ascending=False).head(limit)
    
    def delete(self, record_id: str) -> bool:
        df = self._load_records()
        if df.empty:
            return False
        
        filtered = df[df["id"] != record_id]
        if len(filtered) == len(df):
            return False
        
        filtered.to_parquet(self.records_file, compression="snappy", index=False)
        self.logger.info(f"Deleted backtest record: {record_id}")
        return True
    
    def compare(self, record_ids: list[str]) -> pd.DataFrame:
        df = self._load_records()
        if df.empty:
            return pd.DataFrame()
        
        filtered = df[df["id"].isin(record_ids)]
        return filtered.sort_values("created_at", ascending=False)
    
    def get_statistics(self) -> dict[str, Any]:
        df = self._load_records()
        if df.empty:
            return {
                "total_records": 0,
                "avg_return": 0.0,
                "best_return": 0.0,
                "worst_return": 0.0,
            }
        
        return {
            "total_records": len(df),
            "avg_return": df["total_return"].mean(),
            "best_return": df["total_return"].max(),
            "worst_return": df["total_return"].min(),
            "avg_sharpe": df["sharpe_ratio"].mean(),
            "total_trades": df["total_trades"].sum(),
        }