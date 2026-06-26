from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from src.core.logger import get_logger


@dataclass
class JobConfig:
    name: str
    func: Callable
    trigger_type: str = "cron"
    cron_hour: int = 16
    cron_minute: int = 0
    cron_day_of_week: str = "mon-fri"
    args: tuple = ()
    kwargs: dict[str, Any] = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class SchedulerService:
    
    def __init__(self):
        self._logger = get_logger(self.__class__.__name__)
        self._scheduler = None
        self._jobs = []
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def add_job(self, job_config: JobConfig) -> bool:
        try:
            self._jobs.append(job_config)
            self._logger.info(
                "Job added to scheduler",
                name=job_config.name,
                trigger=f"{job_config.trigger_type}: {job_config.cron_hour}:{job_config.cron_minute}",
            )
            return True
        except Exception as e:
            self._logger.error(f"Failed to add job {job_config.name}", error=str(e))
            return False
    
    def remove_job(self, job_name: str) -> bool:
        try:
            self._jobs = [j for j in self._jobs if j.name != job_name]
            self._logger.info("Job removed", name=job_name)
            return True
        except Exception as e:
            self._logger.error(f"Failed to remove job {job_name}", error=str(e))
            return False
    
    def start(self) -> bool:
        if self._running:
            self._logger.warning("Scheduler is already running")
            return False
        
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            self._scheduler = BlockingScheduler()
            
            for job_config in self._jobs:
                trigger = CronTrigger(
                    day_of_week=job_config.cron_day_of_week,
                    hour=job_config.cron_hour,
                    minute=job_config.cron_minute,
                )
                
                self._scheduler.add_job(
                    job_config.func,
                    trigger=trigger,
                    args=job_config.args,
                    kwargs=job_config.kwargs,
                    name=job_config.name,
                )
                
                self._logger.info(
                    "Job scheduled",
                    name=job_config.name,
                    trigger=f"{job_config.cron_day_of_week} {job_config.cron_hour}:{job_config.cron_minute}",
                )
            
            self._running = True
            self._logger.info("Scheduler started")
            
            self._scheduler.start()
            
            return True
            
        except ImportError:
            self._logger.error(
                "APScheduler not installed. Install with: pip install apscheduler"
            )
            return False
        except Exception as e:
            self._logger.error("Failed to start scheduler", error=str(e))
            return False
    
    def stop(self) -> bool:
        if not self._running:
            return True
        
        try:
            if self._scheduler:
                self._scheduler.shutdown(wait=False)
                self._scheduler = None
            
            self._running = False
            self._logger.info("Scheduler stopped")
            return True
        except Exception as e:
            self._logger.error("Failed to stop scheduler", error=str(e))
            return False
    
    def list_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": job.name,
                "trigger_type": job.trigger_type,
                "cron": f"{job.cron_day_of_week} {job.cron_hour}:{job.cron_minute}",
            }
            for job in self._jobs
        ]


def create_daily_update_job(
    pipeline_func: Callable,
    target_date: date | None = None,
    codes: list[str] | None = None,
    lookback_days: int = 30,
) -> JobConfig:
    if target_date is None:
        target_date = date.today()
    
    return JobConfig(
        name="daily_data_update",
        func=pipeline_func,
        trigger_type="cron",
        cron_hour=16,
        cron_minute=0,
        cron_day_of_week="mon-fri",
        args=(target_date,),
        kwargs={
            "codes": codes,
            "lookback_days": lookback_days,
        },
    )