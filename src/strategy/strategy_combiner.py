from abc import ABC, abstractmethod
from dataclasses import dataclass

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


class StrategyCombiner:
    """
    多策略组合器
    
    支持两种数据模式：
    1. 统一数据模式（默认）：所有策略共享同一份 prepared 数据
    2. 独立数据模式：每个策略独立 prepare（兼容旧接口）
    """
    
    def __init__(
        self,
        combiner: BaseStrategyCombiner | None = None,
        unified_data: bool = True,
    ):
        self.combiner = combiner or WeightedAverageCombiner()
        self.strategies: list[BaseStrategy] = []
        self.unified_data = unified_data
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        self.strategies.append(strategy)
    
    def remove_strategy(self, strategy_name: str) -> bool:
        for i, s in enumerate(self.strategies):
            if s.strategy_name == strategy_name:
                self.strategies.pop(i)
                return True
        return False
    
    def get_strategy(self, strategy_name: str) -> BaseStrategy | None:
        for s in self.strategies:
            if s.strategy_name == strategy_name:
                return s
        return None
    
    def prepare_combined(self, df: pd.DataFrame) -> pd.DataFrame | dict[str, pd.DataFrame]:
        """
        准备数据：
        - 统一模式：返回一份全量指标 DataFrame
        - 独立模式：返回 dict[strategy_name -> DataFrame]
        """
        if self.unified_data and self.strategies:
            # 统一模式：用第一个策略 prepare 即可（指标都一样）
            return self.strategies[0].prepare(df)
        
        prepared = {}
        for strategy in self.strategies:
            prepared[strategy.strategy_name] = strategy.prepare(df)
        return prepared
    
    def score_stock_unified(
        self,
        code: str,
        stock_data: pd.DataFrame,
    ) -> tuple[float, dict[str, float]]:
        """
        统一数据模式下对单只股票评分

        返回：(综合评分, {策略名: 分项得分})
        """
        scores = []
        detail_scores = {}

        for strategy in self.strategies:
            score = strategy.score_stock(code, stock_data)
            scores.append(StrategyScore(
                strategy_name=strategy.strategy_name,
                score=score,
            ))
            detail_scores[strategy.strategy_name] = round(score, 2)

        combined = self.combiner.combine(scores)
        return combined, detail_scores

    def get_completeness_info(self) -> dict[str, dict]:
        """
        收集所有子策略最近一次评分的完整度信息。

        返回：{策略名: {completeness, missing_factors}}
        """
        info = {}
        for strategy in self.strategies:
            if hasattr(strategy, "get_score_completeness"):
                info[strategy.strategy_name] = strategy.get_score_completeness()
            else:
                info[strategy.strategy_name] = {"completeness": "unknown", "missing_factors": []}
        return info
    
    def get_weights_info(self) -> dict[str, float]:
        """获取当前融合权重"""
        if isinstance(self.combiner, WeightedAverageCombiner):
            return dict(self.combiner.weights) if self.combiner.weights else {}
        return {}