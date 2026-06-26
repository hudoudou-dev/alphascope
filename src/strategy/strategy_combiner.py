from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.strategy.base_strategy import BaseStrategy


@dataclass
class StrategyScore:
    strategy_name: str
    score: float
    weight: float = 1.0
    
    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


class BaseStrategyCombiner(ABC):
    
    @abstractmethod
    def combine(self, scores: list[StrategyScore]) -> float:
        pass


class WeightedAverageCombiner(BaseStrategyCombiner):
    
    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or {}
    
    def combine(self, scores: list[StrategyScore]) -> float:
        if not scores:
            return 50.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for score in scores:
            weight = self.weights.get(score.strategy_name, score.weight)
            weighted_sum += score.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50.0
        
        return weighted_sum / total_weight


class VotingCombiner(BaseStrategyCombiner):
    
    def __init__(self, threshold: float = 60.0):
        self.threshold = threshold
    
    def combine(self, scores: list[StrategyScore]) -> float:
        if not scores:
            return 50.0
        
        buy_votes = sum(1 for s in scores if s.score >= self.threshold)
        sell_votes = sum(1 for s in scores if s.score <= (100 - self.threshold))
        
        if buy_votes > len(scores) / 2:
            return 75.0
        if sell_votes > len(scores) / 2:
            return 25.0
        
        return 50.0


class StrategyCombiner:
    
    def __init__(self, combiner: BaseStrategyCombiner | None = None):
        self.combiner = combiner or WeightedAverageCombiner()
        self.strategies: list[BaseStrategy] = []
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        self.strategies.append(strategy)
    
    def remove_strategy(self, strategy_name: str) -> bool:
        for i, s in enumerate(self.strategies):
            if s.strategy_name == strategy_name:
                self.strategies.pop(i)
                return True
        return False
    
    def prepare_combined(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        prepared = {}
        for strategy in self.strategies:
            prepared[strategy.strategy_name] = strategy.prepare(df)
        return prepared
    
    def score_combined(
        self,
        code: str,
        daily_data: dict[str, pd.Series],
    ) -> float:
        scores = []
        
        for strategy in self.strategies:
            if strategy.strategy_name not in daily_data:
                continue
            
            score = strategy.score_stock(code, daily_data[strategy.strategy_name])
            scores.append(StrategyScore(
                strategy_name=strategy.strategy_name,
                score=score,
            ))
        
        return self.combiner.combine(scores)
    
    def execute_combined(
        self,
        df: pd.DataFrame,
        ctx: Any,
    ) -> dict[str, list[str]]:
        prepared = self.prepare_combined(df)
        
        daily_data_map = {}
        for strategy_name, prepared_df in prepared.items():
            code_df = prepared_df[prepared_df["code"] == ctx.positions.keys()]
            if not code_df.empty:
                daily_data_map[strategy_name] = code_df.iloc[-1]
        
        combined_scores = {}
        for code in ctx.positions.keys():
            if code in daily_data_map:
                combined_scores[code] = self.score_combined(code, daily_data_map)
        
        buy_signals = [code for code, score in combined_scores.items() if score >= 60]
        sell_signals = [code for code, score in combined_scores.items() if score <= 40]
        
        return {
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "scores": combined_scores,
        }