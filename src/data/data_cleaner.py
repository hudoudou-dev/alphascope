from pathlib import Path
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger


class DataCleaner:
    
    def __init__(self, data_path: str | Path | None = None):
        if data_path is None:
            data_path = Path(config_loader.get("data.storage.base_path", "./data"))
        self.data_path = Path(data_path)
        self.logger = get_logger(self.__class__.__name__)
    
    def get_file_info(self, code: str) -> dict | None:
        file_path = self.data_path / f"{code}.parquet"
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            "path": str(file_path),
            "size_kb": stat.st_size / 1024,
            "modified": datetime.fromtimestamp(stat.st_mtime),
        }
    
    def calculate_data_age(self, code: str) -> int | None:
        df = self.load_metadata(code)
        if df is None or df.empty:
            return None
        
        if "date" not in df.columns:
            return None
        
        latest_date = pd.to_datetime(df["date"]).max()
        return (datetime.now() - latest_date).days
    
    def load_metadata(self, code: str) -> pd.DataFrame | None:
        file_path = self.data_path / f"{code}.parquet"
        if not file_path.exists():
            return None
        
        try:
            return pd.read_parquet(file_path)
        except Exception:
            return None
    
    def clean_old_files(
        self,
        days_threshold: int = 365,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        deleted_files = []
        skipped_files = []
        
        if not self.data_path.exists():
            return {"deleted": [], "skipped": [], "success": True}
        
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        
        for file in self.data_path.glob("*.parquet"):
            try:
                stat = file.stat()
                modified_date = datetime.fromtimestamp(stat.st_mtime)
                
                if modified_date < threshold_date:
                    if not dry_run:
                        file.unlink()
                    deleted_files.append(file.stem)
                else:
                    skipped_files.append(file.stem)
            except Exception as e:
                self.logger.warning(f"Failed to process {file}: {e}")
        
        result = {
            "deleted": deleted_files,
            "skipped": skipped_files,
            "success": True,
            "dry_run": dry_run,
            "threshold_days": days_threshold,
        }
        
        self.logger.info(
            f"Cleaned {'(dry run) ' if dry_run else ''}{len(deleted_files)} files, "
            f"skipped {len(skipped_files)} files"
        )
        
        return result
    
    def archive_old_data(
        self,
        days_threshold: int = 180,
        archive_path: str | Path | None = None,
    ) -> dict[str, Any]:
        if archive_path is None:
            archive_path = self.data_path.parent / "archive"
        archive_path = Path(archive_path)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        archived_files = []
        failed_files = []
        
        if not self.data_path.exists():
            return {"archived": [], "failed": [], "success": False}
        
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        
        for file in self.data_path.glob("*.parquet"):
            try:
                df = pd.read_parquet(file)
                if "date" not in df.columns:
                    continue
                
                latest_date = pd.to_datetime(df["date"]).max()
                
                if (datetime.now() - latest_date).days > days_threshold:
                    target_file = archive_path / file.name
                    df.to_parquet(target_file, compression="snappy")
                    file.unlink()
                    archived_files.append(file.stem)
            except Exception as e:
                self.logger.warning(f"Failed to archive {file}: {e}")
                failed_files.append(file.stem)
        
        return {
            "archived": archived_files,
            "failed": failed_files,
            "success": len(failed_files) == 0,
            "archive_path": str(archive_path),
        }
    
    def apply_sliding_window(
        self,
        code: str,
        keep_days: int = 90,
    ) -> bool:
        file_path = self.data_path / f"{code}.parquet"
        if not file_path.exists():
            return False
        
        try:
            df = pd.read_parquet(file_path)
            if "date" not in df.columns:
                return False
            
            threshold_date = datetime.now() - timedelta(days=keep_days)
            df["date"] = pd.to_datetime(df["date"])
            
            original_len = len(df)
            df = df[df["date"] >= threshold_date]
            
            if len(df) < original_len:
                df.to_parquet(file_path, compression="snappy", index=False)
                self.logger.info(
                    f"Applied sliding window to {code}: "
                    f"{original_len} -> {len(df)} rows"
                )
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to apply sliding window to {code}: {e}")
            return False
    
    def get_storage_summary(self) -> dict[str, Any]:
        if not self.data_path.exists():
            return {"total_files": 0, "total_size_mb": 0, "files": []}
        
        files_info = []
        total_size = 0
        
        for file in self.data_path.glob("*.parquet"):
            stat = file.stat()
            total_size += stat.st_size
            
            df = self.load_metadata(file.stem)
            rows = len(df) if df is not None else 0
            start_date = df["date"].min() if df is not None and "date" in df.columns else None
            end_date = df["date"].max() if df is not None and "date" in df.columns else None
            
            files_info.append({
                "code": file.stem,
                "size_kb": stat.st_size / 1024,
                "rows": rows,
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
            })
        
        return {
            "total_files": len(files_info),
            "total_size_mb": total_size / (1024 * 1024),
            "files": files_info,
        }