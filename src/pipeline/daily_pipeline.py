from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from src.backtest.backtest_engine import BacktestEngine, BacktestResult
from src.backtest.slippage import FixedSlippageModel
from src.calendar.trading_calendar import TradingCalendarService
from src.core.config import config_loader
from src.core.logger import get_logger
from src.notifier.notification_manager import (
    BaseNotifier,
    DingTalkNotifier,
    EventType,
    FeishuNotifier,
    NotificationMessage,
)


@dataclass
class DailyPipeline:
    trading_calendar: TradingCalendarService | None = None
    notifier: BaseNotifier | None = None
    strategy = None
    initial_cash: float = 1000000.0
    
    _data_path: Path | None = field(default=None, init=False, repr=False)
    _logger: Any = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        self._logger = get_logger(self.__class__.__name__)
        config = config_loader.get("data", {}).get("storage", {})
        base_path = config.get("base_path", "./data")
        self._data_path = Path(base_path)
    
    def is_trading_day(self, check_date: date | None = None) -> bool:
        if check_date is None:
            check_date = date.today()
        
        if self.trading_calendar is None:
            return True
        
        try:
            return self.trading_calendar.is_trading_day(check_date)
        except Exception:
            return True
    
    def update_calendar(self, end_date: date | None = None) -> bool:
        if self.trading_calendar is None:
            return True
        
        if end_date is None:
            end_date = date.today()
        
        try:
            self.trading_calendar.update_trading_days(end_date)
            self._logger.info("Trading calendar updated", end_date=str(end_date))
            return True
        except Exception as e:
            self._logger.error("Failed to update calendar", error=str(e))
            return False
    
    def download_data(
        self,
        codes: list[str],
        start_date: date,
        end_date: date,
        adjust: str = "qfq",
    ) -> dict[str, Any]:
        result = {
            "success": True,
            "downloaded": [],
            "failed": [],
            "errors": [],
        }
        
        if self._data_path is None:
            result["success"] = False
            result["errors"].append("Data path not configured")
            return result
        
        self._data_path.mkdir(parents=True, exist_ok=True)
        
        from src.data.providers.akshare_provider import AKShareProvider
        provider = AKShareProvider()
        
        for code in codes:
            try:
                df = provider.download_and_save(
                    code=code,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    adjust=adjust,
                )
                
                if not df.empty:
                    result["downloaded"].append(code)
                    self._logger.info(f"Downloaded {code}: {len(df)} rows")
                else:
                    result["failed"].append(code)
                    result["errors"].append(f"{code}: No data returned")
                    
            except Exception as e:
                result["failed"].append(code)
                result["errors"].append(f"{code}: {str(e)}")
                self._logger.error(f"Failed to download {code}", error=str(e))
        
        if result["failed"]:
            result["success"] = False
        
        return result
    
    def load_data(
        self,
        codes: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        if self._data_path is None or not self._data_path.exists():
            return pd.DataFrame()
        
        all_data = []
        
        for code in codes:
            file_path = self._data_path / f"{code}.parquet"
            if not file_path.exists():
                continue
            
            try:
                df = pd.read_parquet(file_path)
                df["date"] = pd.to_datetime(df["date"])
                df["code"] = code
                
                if start_date:
                    df = df[df["date"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["date"] <= pd.to_datetime(end_date)]
                
                all_data.append(df)
                
            except Exception as e:
                self._logger.warning(f"Failed to load {code}", error=str(e))
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)
    
    def run_backtest(
        self,
        stock_data: pd.DataFrame,
        strategy: Any,
        use_trading_calendar: bool = True,
        slippage_rate: float = 0.001,
    ) -> BacktestResult | None:
        if stock_data.empty:
            self._logger.warning("No data for backtest")
            return None
        
        slippage_model = FixedSlippageModel(slippage_rate=slippage_rate)
        
        engine = BacktestEngine(
            strategy=strategy,
            initial_cash=self.initial_cash,
            trading_calendar=self.trading_calendar if use_trading_calendar else None,
            use_trading_calendar=use_trading_calendar,
            slippage_model=slippage_model,
        )
        
        try:
            result = engine.run(stock_data)
            self._logger.info(
                "Backtest completed",
                total_return=result.total_return,
                total_trades=result.total_trades,
            )
            return result
        except Exception as e:
            self._logger.error("Backtest failed", error=str(e))
            return None
    
    def send_notification(
        self,
        event_type: EventType,
        message: str,
        strategy_name: str | None = None,
        extra_data: dict | None = None,
    ) -> bool:
        if self.notifier is None:
            self._logger.info("Notifier not configured, skipping notification")
            return True
        
        notification = NotificationMessage(
            event_type=event_type,
            message=message,
            strategy_name=strategy_name,
            extra_data=extra_data,
        )
        
        try:
            return self.notifier.send(notification)
        except Exception as e:
            self._logger.error("Failed to send notification", error=str(e))
            return False
    
    def run(
        self,
        target_date: date | None = None,
        codes: list[str] | None = None,
        strategy: Any | None = None,
        lookback_days: int = 30,
    ) -> dict[str, Any]:
        if target_date is None:
            target_date = date.today()
        
        self._logger.info("Starting daily pipeline", target_date=str(target_date))
        
        pipeline_result = {
            "date": target_date.isoformat(),
            "success": False,
            "is_trading_day": self.is_trading_day(target_date),
            "download_result": None,
            "backtest_result": None,
            "notification_sent": False,
            "error": None,
        }
        
        if not pipeline_result["is_trading_day"]:
            self._logger.info(f"{target_date} is not a trading day, skipping")
            pipeline_result["success"] = True
            return pipeline_result
        
        if not self.update_calendar(target_date):
            pipeline_result["error"] = "Failed to update trading calendar"
            return pipeline_result
        
        if codes is None:
            codes = self._get_default_codes()
        
        if not codes:
            pipeline_result["error"] = "No stock codes provided"
            return pipeline_result
        
        start_date = target_date - timedelta(days=lookback_days)
        
        download_result = self.download_data(
            codes=codes,
            start_date=start_date,
            end_date=target_date,
        )
        pipeline_result["download_result"] = download_result
        
        if not download_result["downloaded"]:
            pipeline_result["error"] = "No data downloaded"
            return pipeline_result
        
        stock_data = self.load_data(
            codes=download_result["downloaded"],
            start_date=start_date,
            end_date=target_date,
        )
        
        if stock_data.empty:
            pipeline_result["error"] = "No data available for backtest"
            return pipeline_result
        
        if strategy is None:
            from src.web.app import SimpleMAStrategy
            strategy = SimpleMAStrategy()
        
        backtest_result = self.run_backtest(stock_data, strategy)
        pipeline_result["backtest_result"] = backtest_result.to_dict() if backtest_result else None
        
        notification_sent = self.send_notification(
            event_type=EventType.DAILY_REPORT,
            message=self._build_report_message(target_date, download_result, backtest_result),
            strategy_name=strategy.strategy_name if hasattr(strategy, 'strategy_name') else None,
            extra_data={
                "download_count": len(download_result["downloaded"]),
                "backtest_return": backtest_result.total_return if backtest_result else None,
            },
        )
        pipeline_result["notification_sent"] = notification_sent
        
        pipeline_result["success"] = True
        self._logger.info("Daily pipeline completed successfully")
        
        return pipeline_result
    
    def _get_default_codes(self) -> list[str]:
        return ["600000.SH", "000001.SZ", "300750.SZ"]
    
    def _build_report_message(
        self,
        target_date: date,
        download_result: dict,
        backtest_result: BacktestResult | None,
    ) -> str:
        message = f"📊 AlphaScope 每日报告 - {target_date.isoformat()}\n\n"
        message += f"✅ 数据下载成功: {len(download_result.get('downloaded', []))} 只\n"
        
        if download_result.get("failed"):
            message += f"❌ 下载失败: {len(download_result['failed'])} 只\n"
        
        if backtest_result:
            message += f"\n📈 回测结果:\n"
            message += f"  总收益率: {backtest_result.total_return:.2f}%\n"
            message += f"  年化收益率: {backtest_result.annual_return:.2f}%\n"
            message += f"  最大回撤: {backtest_result.max_drawdown:.2f}%\n"
            message += f"  交易次数: {backtest_result.total_trades}\n"
            message += f"  胜率: {backtest_result.win_rate:.1f}%\n"
        
        return message


def create_pipeline(
    config: dict | None = None,
    notifier_type: str = "dingtalk",
) -> DailyPipeline:
    if config is None:
        config = {}
    
    notifier = None
    notifier_config = config.get("notifier", {})
    webhook_url = notifier_config.get("webhook_url")
    
    if webhook_url:
        try:
            if notifier_type.lower() == "dingtalk":
                notifier = DingTalkNotifier(webhook_url=webhook_url)
            elif notifier_type.lower() == "feishu":
                notifier = FeishuNotifier(webhook_url=webhook_url)
        except Exception as e:
            pass
    
    trading_calendar = None
    calendar_enabled = config.get("trading_calendar_enabled", True)
    
    if calendar_enabled:
        try:
            trading_calendar = TradingCalendarService()
        except Exception:
            pass
    
    return DailyPipeline(
        trading_calendar=trading_calendar,
        notifier=notifier,
        initial_cash=config.get("initial_cash", 1000000.0),
    )