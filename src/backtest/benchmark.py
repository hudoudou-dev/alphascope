from dataclasses import dataclass
from typing import Literal

import pandas as pd

from src.core.logger import get_logger


@dataclass
class BenchmarkResult:
    alpha: float
    beta: float
    tracking_error: float
    information_ratio: float
    correlation: float
    r_squared: float
    
    def to_dict(self) -> dict:
        return {
            "alpha": self.alpha,
            "beta": self.beta,
            "tracking_error": self.tracking_error,
            "information_ratio": self.information_ratio,
            "correlation": self.correlation,
            "r_squared": self.r_squared,
        }


class Benchmark:
    
    def __init__(
        self,
        index_code: Literal["000300.SH", "000905.SH", "000001.SH"] = "000300.SH",
        name: str | None = None,
    ):
        self.index_code = index_code
        self.name = name or index_code
        self.logger = get_logger(self.__class__.__name__)
        self._benchmark_data: pd.DataFrame | None = None
    
    def load_benchmark_data(
        self,
        start_date: str,
        end_date: str,
        data_path: str = "./data",
    ) -> bool:
        from pathlib import Path
        import pandas as pd
        
        file_path = Path(data_path) / f"{self.index_code}.parquet"
        if not file_path.exists():
            self.logger.warning(f"Benchmark file not found: {file_path}")
            return False
        
        try:
            self._benchmark_data = pd.read_parquet(file_path)
            self._benchmark_data["date"] = pd.to_datetime(self._benchmark_data["date"])
            self._benchmark_data = self._benchmark_data[
                (self._benchmark_data["date"] >= start_date) &
                (self._benchmark_data["date"] <= end_date)
            ]
            self._benchmark_data = self._benchmark_data.sort_values("date")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load benchmark data: {e}")
            return False
    
    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        return prices.pct_change().fillna(0)
    
    def calculate_alpha_beta(
        self,
        strategy_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> tuple[float, float]:
        if len(strategy_returns) != len(benchmark_returns) or len(strategy_returns) < 2:
            return 0.0, 1.0
        
        mean_strategy = strategy_returns.mean()
        mean_benchmark = benchmark_returns.mean()
        
        covariance = ((strategy_returns - mean_strategy) * (benchmark_returns - mean_benchmark)).mean()
        variance_benchmark = benchmark_returns.var()
        
        if variance_benchmark == 0:
            return 0.0, 1.0
        
        beta = covariance / variance_benchmark
        alpha = (mean_strategy - beta * mean_benchmark) * 252
        
        return alpha, beta
    
    def analyze(
        self,
        strategy_values: pd.Series | pd.DataFrame,
        dates: pd.Series | pd.DataFrame | None = None,
    ) -> BenchmarkResult:
        if isinstance(strategy_values, pd.DataFrame):
            if "total_value" in strategy_values.columns:
                strategy_values = strategy_values["total_value"]
            elif len(strategy_values.columns) > 0:
                strategy_values = strategy_values.iloc[:, 0]
        
        strategy_returns = self.calculate_returns(strategy_values)
        
        if self._benchmark_data is None:
            self.logger.warning("No benchmark data loaded, using synthetic benchmark")
            benchmark_returns = pd.Series([0.0001] * len(strategy_returns))
        else:
            benchmark_returns = self.calculate_returns(self._benchmark_data["close_price"])
            
            if len(benchmark_returns) != len(strategy_returns):
                min_len = min(len(benchmark_returns), len(strategy_returns))
                strategy_returns = strategy_returns[:min_len]
                benchmark_returns = benchmark_returns[:min_len]
        
        alpha, beta = self.calculate_alpha_beta(strategy_returns, benchmark_returns)
        
        tracking_error = (strategy_returns - benchmark_returns).std() * (252 ** 0.5)
        
        excess_returns = strategy_returns - benchmark_returns
        information_ratio = (
            excess_returns.mean() / excess_returns.std() * (252 ** 0.5)
            if excess_returns.std() > 0 else 0.0
        )
        
        correlation = strategy_returns.corr(benchmark_returns)
        
        r_squared = beta ** 2 if beta != 0 else 0.0
        
        return BenchmarkResult(
            alpha=alpha,
            beta=beta,
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            correlation=correlation,
            r_squared=r_squared,
        )
    
    def compare_with_benchmark(
        self,
        strategy_returns: pd.Series,
        benchmark_name: str = "沪深300",
    ) -> dict:
        if self._benchmark_data is None:
            return {
                "benchmark": benchmark_name,
                "error": "No benchmark data available",
            }
        
        bench_returns = self.calculate_returns(self._benchmark_data["close_price"])
        
        alpha, beta = self.calculate_alpha_beta(strategy_returns, bench_returns)
        
        total_strategy_return = (1 + strategy_returns).prod() - 1
        total_benchmark_return = (1 + bench_returns).prod() - 1
        
        return {
            "benchmark": benchmark_name,
            "strategy_total_return": total_strategy_return * 100,
            "benchmark_total_return": total_benchmark_return * 100,
            "excess_return": (total_strategy_return - total_benchmark_return) * 100,
            "alpha": alpha,
            "beta": beta,
        }