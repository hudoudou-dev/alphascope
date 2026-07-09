"""
共享依赖：路径解析、Provider 实例、下载任务管理（支持 WebSocket 推送）
"""

import asyncio
import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.core.config import config_loader
from src.core.logger import get_logger
from src.data.providers.akshare_provider import AKShareProvider
from src.data.providers.baostock_provider import BaoStockProvider
from src.data.providers.tushare_provider import TushareProvider
from src.web.utils import normalize_stock_code

logger = get_logger("APIDeps")


def get_raw_data_path() -> Path:
    base_path = config_loader.get("data.storage.base_path", "./data")
    return Path(base_path) / "raw"


def get_processed_data_path() -> Path:
    base_path = config_loader.get("data.storage.base_path", "./data")
    return Path(base_path) / "processed"


def get_config_path() -> Path:
    return config_loader.config_path


# ==================== 下载任务管理 ====================

@dataclass
class DownloadTask:
    task_id: str
    codes: list[str]
    start_date: datetime
    end_date: datetime
    adjust: str = "qfq"
    status: str = "pending"
    error: str | None = None
    completed: int = 0
    failed: int = 0
    total: int = 0
    current_code: str = ""
    current_provider: str = ""
    is_running: bool = False
    start_time: datetime | None = None
    logs: deque = field(default_factory=lambda: deque(maxlen=200))

    @property
    def progress_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed + self.failed) / self.total * 100

    @property
    def eta(self) -> str:
        if self.start_time is None or self.completed == 0:
            return "计算中..."
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time = elapsed / self.completed
        remaining = (self.total - self.completed - self.failed) * avg_time
        if remaining < 60:
            return f"{int(remaining)}秒"
        elif remaining < 3600:
            return f"{int(remaining / 60)}分钟"
        else:
            return f"{int(remaining / 3600)}小时"


class DownloadTaskManager:
    """管理后台下载任务 + WebSocket 实时推送"""

    def __init__(self):
        self._tasks: dict[str, DownloadTask] = {}
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

        self.providers = {
            "akshare": AKShareProvider,
            "baostock": BaoStockProvider,
            "tushare": TushareProvider,
        }
        self.provider_order = ["akshare", "baostock", "tushare"]

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """设置主事件循环（在 FastAPI startup 中调用）"""
        self._loop = loop

    def start_download(
        self,
        codes: list[str],
        start_date: datetime,
        end_date: datetime,
        adjust: str = "qfq",
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        task = DownloadTask(
            task_id=task_id,
            codes=codes,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            total=len(codes),
            start_time=datetime.now(),
            is_running=True,
        )

        with self._lock:
            self._tasks[task_id] = task
            self._subscribers[task_id] = []

        thread = threading.Thread(
            target=self._download_worker,
            args=(task_id,),
            daemon=True,
        )
        thread.start()
        return task_id

    def _download_worker(self, task_id: str):
        task = self._tasks[task_id]
        provider_index = 0

        try:
            for code in task.codes:
                if not task.is_running:
                    break

                with self._lock:
                    task.current_code = code

                self._notify(task_id)

                success = False
                retry_count = 0
                max_retries = 3

                while not success and retry_count < max_retries:
                    try:
                        provider_name = self.provider_order[provider_index]
                        with self._lock:
                            task.current_provider = provider_name

                        self._notify(task_id)

                        provider = self.providers[provider_name]()
                        df = provider.download_and_save(
                            code=code,
                            start_date=task.start_date,
                            end_date=task.end_date,
                            adjust=task.adjust,
                        )

                        if not df.empty:
                            with self._lock:
                                task.completed += 1
                                task.logs.append(f"[SUCCESS] {code} 下载成功（{provider_name}），{len(df)} 行")
                            success = True
                            self._notify(task_id)
                        else:
                            raise Exception("数据为空")

                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e)[:200]
                        with self._lock:
                            task.logs.append(f"[ERROR] {code} 失败（{retry_count}/{max_retries}）: {error_msg}")

                        if retry_count < max_retries and provider_index < len(self.provider_order) - 1:
                            provider_index += 1
                            with self._lock:
                                task.logs.append(f"[WARNING] {code} 切换到 {self.provider_order[provider_index]}")
                            self._notify(task_id)
                            time.sleep(1)
                        else:
                            with self._lock:
                                task.failed += 1
                                task.logs.append(f"[ERROR] {code} 所有数据源均失败: {error_msg}")
                            self._notify(task_id)
                            break

                time.sleep(0.1)

        except Exception as e:
            with self._lock:
                task.logs.append(f"[ERROR] 下载线程异常: {str(e)[:200]}")
        finally:
            with self._lock:
                task.is_running = False
                task.current_code = ""
                task.current_provider = ""
                task.logs.append(
                    f"[INFO] 下载完成：成功 {task.completed}，失败 {task.failed}"
                )
            self._notify(task_id)
            self._close_subscribers(task_id)

    def _notify(self, task_id: str):
        """向所有 WebSocket 订阅者推送当前任务状态（线程安全）"""
        task = self._tasks.get(task_id)
        if not task:
            return

        msg = json.dumps({
            "task_id": task.task_id,
            "total": task.total,
            "completed": task.completed,
            "failed": task.failed,
            "current_code": task.current_code,
            "current_provider": task.current_provider,
            "is_running": task.is_running,
            "progress_pct": round(task.progress_pct, 1),
            "eta": task.eta,
            "logs": list(task.logs)[-20:],
        }, default=str, ensure_ascii=False)

        if self._loop is None:
            return

        for q in self._subscribers.get(task_id, []):
            try:
                self._loop.call_soon_threadsafe(self._safe_put, q, msg)
            except Exception:
                pass

    def _safe_put(self, q: asyncio.Queue, msg: str | None):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass

    def _close_subscribers(self, task_id: str):
        """任务结束后关闭所有订阅者（线程安全）"""
        if self._loop is None:
            return

        for q in self._subscribers.get(task_id, []):
            try:
                self._loop.call_soon_threadsafe(self._safe_put, q, None)
            except Exception:
                pass

    async def subscribe(self, task_id: str) -> asyncio.Queue | None:
        """订阅任务进度推送，返回一个异步队列"""
        task = self._tasks.get(task_id)
        if task is None:
            return None

        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(q)

        if not task.is_running:
            await q.put(self._build_status_msg(task_id))

        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue):
        """取消订阅"""
        subs = self._subscribers.get(task_id, [])
        if q in subs:
            subs.remove(q)

    def _build_status_msg(self, task_id: str) -> str:
        task = self._tasks.get(task_id)
        if not task:
            return json.dumps({"error": "task not found"})
        return json.dumps({
            "task_id": task.task_id,
            "total": task.total,
            "completed": task.completed,
            "failed": task.failed,
            "current_code": task.current_code,
            "current_provider": task.current_provider,
            "is_running": task.is_running,
            "progress_pct": round(task.progress_pct, 1),
            "eta": task.eta,
            "logs": list(task.logs)[-20:],
        }, default=str, ensure_ascii=False)

    def get_task(self, task_id: str) -> DownloadTask | None:
        return self._tasks.get(task_id)

    def stop_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.is_running = False
            self._notify(task_id)
            return True
        return False


download_task_manager = DownloadTaskManager()


def parse_stock_codes(codes: list[str]) -> list[str]:
    """标准化股票代码列表"""
    return [normalize_stock_code(c.strip()) for c in codes if c.strip()]
