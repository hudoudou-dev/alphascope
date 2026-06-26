"""
选股策略类

结合用户配置的超参进行评分，包括：
- 市值区间筛选
- 股价区间筛选
- 涨跌停配置筛选
- 均线排列评分
- 价格位置评分
- 趋势强度评分
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger
from src.indicators.technical_indicators import TechnicalIndicators
from src.strategy.base_strategy import BaseStrategy


@dataclass
class SelectionConfig:
    """选股策略配置"""
    # 市值与价格区间
    market_cap_min: float = 50.0  # 最小市值（亿元）
    market_cap_max: float = 20000.0  # 最大市值（亿元）
    price_min: float = 5.0  # 最小股价（元）
    price_max: float = 2000.0  # 最大股价（元）
    
    # 涨跌停配置
    limit_up_min: int = 0  # 最小涨停次数
    limit_down_max: int = 3  # 最大跌停次数
    limit_stat_period: int = 20  # 涨跌停统计周期（天）
    max_up_threshold: float = 10.0  # 最大涨幅阈值（%）
    max_down_threshold: float = -10.0  # 最大跌幅阈值（%）
    
    # 持仓配置
    initial_cash: float = 1000000.0  # 初始资金量（元）
    max_positions: int = 10  # 最大持仓股票数量
    top_n: int = 20  # 候选股票数量（Top-N）
    min_score_threshold: float = 70.0  # 最小评分阈值（提高到70.0，降低交易频率）
    
    # 交易频率控制
    cooldown_days: int = 5  # 冷却期（卖出后多少天内不能重新买入同一只股票）
    max_trades_per_day: int = 5  # 每天最大交易次数
    
    # 评分权重配置
    ma_alignment_weight: float = 40.0  # 均线排列权重（%）
    price_position_weight: float = 30.0  # 价格位置权重（%）
    trend_strength_weight: float = 30.0  # 趋势强度权重（%）
    
    # 均线排列评分参数
    score_ma_perfect_bull: float = 85.0  # 完美多头排列评分
    score_ma_partial_bull: float = 75.0  # 部分多头排列评分
    score_ma_short_bull: float = 65.0  # 短期多头排列评分
    score_ma_perfect_bear: float = 25.0  # 完美空头排列评分
    score_ma_partial_bear: float = 35.0  # 部分空头排列评分
    score_ma_short_bear: float = 45.0  # 短期空头排列评分
    score_ma_neutral: float = 50.0  # 中性评分
    
    # 价格位置评分参数
    score_price_all_above: float = 85.0  # 价格在所有均线之上评分
    score_price_3_above: float = 75.0  # 价格在3条均线之上评分
    score_price_2_above: float = 65.0  # 价格在2条均线之上评分
    score_price_1_above: float = 55.0  # 价格在1条均线之上评分
    score_price_all_below: float = 25.0  # 价格在所有均线之下评分
    score_price_3_below: float = 35.0  # 价格在3条均线之下评分
    score_price_2_below: float = 45.0  # 价格在2条均线之下评分
    score_price_neutral: float = 50.0  # 中性评分
    
    # 趋势强度评分参数
    score_trend_base: float = 50.0  # 基础评分
    score_trend_ma_spread_max: float = 20.0  # 均线发散加分最大值
    score_trend_price_spread_max: float = 15.0  # 价格距离加分最大值
    
    @classmethod
    def from_config(cls) -> "SelectionConfig":
        """从配置文件读取选股策略配置"""
        config = config_loader.get("strategy", {}).get("selection", {})
        
        return cls(
            market_cap_min=config.get("market_cap_min", 50.0),
            market_cap_max=config.get("market_cap_max", 20000.0),
            price_min=config.get("price_min", 5.0),
            price_max=config.get("price_max", 2000.0),
            limit_up_min=config.get("limit_up_min", 0),
            limit_down_max=config.get("limit_down_max", 3),
            limit_stat_period=config.get("limit_stat_period", 20),
            max_up_threshold=config.get("max_up_threshold", 10.0),
            max_down_threshold=config.get("max_down_threshold", -10.0),
            initial_cash=config.get("initial_cash", 1000000.0),
            max_positions=config.get("max_positions", 10),
            top_n=config.get("top_n", 20),
            min_score_threshold=config.get("min_score_threshold", 70.0),
            cooldown_days=config.get("cooldown_days", 5),
            max_trades_per_day=config.get("max_trades_per_day", 5),
            ma_alignment_weight=config.get("ma_alignment_weight", 40.0),
            price_position_weight=config.get("price_position_weight", 30.0),
            trend_strength_weight=config.get("trend_strength_weight", 30.0),
            # 均线排列评分参数
            score_ma_perfect_bull=config.get("score_ma_perfect_bull", 85.0),
            score_ma_partial_bull=config.get("score_ma_partial_bull", 75.0),
            score_ma_short_bull=config.get("score_ma_short_bull", 65.0),
            score_ma_perfect_bear=config.get("score_ma_perfect_bear", 25.0),
            score_ma_partial_bear=config.get("score_ma_partial_bear", 35.0),
            score_ma_short_bear=config.get("score_ma_short_bear", 45.0),
            score_ma_neutral=config.get("score_ma_neutral", 50.0),
            # 价格位置评分参数
            score_price_all_above=config.get("score_price_all_above", 85.0),
            score_price_3_above=config.get("score_price_3_above", 75.0),
            score_price_2_above=config.get("score_price_2_above", 65.0),
            score_price_1_above=config.get("score_price_1_above", 55.0),
            score_price_all_below=config.get("score_price_all_below", 25.0),
            score_price_3_below=config.get("score_price_3_below", 35.0),
            score_price_2_below=config.get("score_price_2_below", 45.0),
            score_price_neutral=config.get("score_price_neutral", 50.0),
            # 趋势强度评分参数
            score_trend_base=config.get("score_trend_base", 50.0),
            score_trend_ma_spread_max=config.get("score_trend_ma_spread_max", 20.0),
            score_trend_price_spread_max=config.get("score_trend_price_spread_max", 15.0),
        )
    
    def to_config_dict(self) -> dict[str, Any]:
        """转换为配置字典"""
        return {
            "market_cap_min": self.market_cap_min,
            "market_cap_max": self.market_cap_max,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "limit_up_min": self.limit_up_min,
            "limit_down_max": self.limit_down_max,
            "limit_stat_period": self.limit_stat_period,
            "max_up_threshold": self.max_up_threshold,
            "max_down_threshold": self.max_down_threshold,
            "initial_cash": self.initial_cash,
            "max_positions": self.max_positions,
            "top_n": self.top_n,
            "min_score_threshold": self.min_score_threshold,
            "cooldown_days": self.cooldown_days,
            "max_trades_per_day": self.max_trades_per_day,
            "ma_alignment_weight": self.ma_alignment_weight,
            "price_position_weight": self.price_position_weight,
            "trend_strength_weight": self.trend_strength_weight,
            # 均线排列评分参数
            "score_ma_perfect_bull": self.score_ma_perfect_bull,
            "score_ma_partial_bull": self.score_ma_partial_bull,
            "score_ma_short_bull": self.score_ma_short_bull,
            "score_ma_perfect_bear": self.score_ma_perfect_bear,
            "score_ma_partial_bear": self.score_ma_partial_bear,
            "score_ma_short_bear": self.score_ma_short_bear,
            "score_ma_neutral": self.score_ma_neutral,
            # 价格位置评分参数
            "score_price_all_above": self.score_price_all_above,
            "score_price_3_above": self.score_price_3_above,
            "score_price_2_above": self.score_price_2_above,
            "score_price_1_above": self.score_price_1_above,
            "score_price_all_below": self.score_price_all_below,
            "score_price_3_below": self.score_price_3_below,
            "score_price_2_below": self.score_price_2_below,
            "score_price_neutral": self.score_price_neutral,
            # 趋势强度评分参数
            "score_trend_base": self.score_trend_base,
            "score_trend_ma_spread_max": self.score_trend_ma_spread_max,
            "score_trend_price_spread_max": self.score_trend_price_spread_max,
        }


class SelectionStrategy(BaseStrategy):
    """选股策略类"""
    
    def __init__(self, config: SelectionConfig | None = None):
        super().__init__(strategy_name="SelectionStrategy")
        
        self.config = config or SelectionConfig.from_config()
        self.logger = get_logger(self.strategy_name)
        
        # 确保权重总和为100%
        total_weight = (
            self.config.ma_alignment_weight
            + self.config.price_position_weight
            + self.config.trend_strength_weight
        )
        
        if total_weight != 100.0:
            self.logger.warning(
                "权重总和不为100%，将自动调整",
                total_weight=total_weight,
            )
            # 自动调整权重
            scale_factor = 100.0 / total_weight
            self.config.ma_alignment_weight *= scale_factor
            self.config.price_position_weight *= scale_factor
            self.config.trend_strength_weight *= scale_factor
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据，计算技术指标"""
        indicators = TechnicalIndicators()
        
        # 计算均线
        df = indicators.add_ma(df, periods=[5, 10, 20, 60])
        
        # 计算涨跌幅
        df["pct_chg"] = df["close_price"].pct_change() * 100
        
        return df
    
    def score_stock(self, code: str, stock_data: pd.DataFrame) -> float:
        """
        对股票进行评分
        
        评分逻辑：
        1. 均线排列评分（权重：ma_alignment_weight）
        2. 价格位置评分（权重：price_position_weight）
        3. 趋势强度评分（权重：trend_strength_weight）
        4. 涨跌停次数评分（基于limit_stat_period参数）
        
        参数：
        - code: 股票代码
        - stock_data: 股票数据（DataFrame，包含limit_stat_period天的数据）
        
        返回：综合评分（0-100）
        """
        # 检查数据是否为空
        if stock_data.empty:
            return 50.0
        
        # 获取最新一天的数据
        latest_data = stock_data.iloc[-1]
        
        # 获取均线数据
        ma5 = latest_data.get("ma5", 0)
        ma10 = latest_data.get("ma10", 0)
        ma20 = latest_data.get("ma20", 0)
        ma60 = latest_data.get("ma60", 0)
        close_price = latest_data.get("close_price", 0)
        
        # 如果数据不完整，返回中性评分
        if ma5 <= 0 or ma10 <= 0 or ma20 <= 0 or close_price <= 0:
            return 50.0
        
        # 1. 均线排列评分（0-100）
        ma_alignment_score = self._score_ma_alignment(
            close_price, ma5, ma10, ma20, ma60
        )
        
        # 2. 价格位置评分（0-100）
        price_position_score = self._score_price_position(
            close_price, ma5, ma10, ma20, ma60
        )
        
        # 3. 趋势强度评分（0-100）
        trend_strength_score = self._score_trend_strength(
            close_price, ma5, ma10, ma20, ma60
        )
        
        # 4. 涨跌停次数评分（0-100）
        limit_stat_score = self._score_limit_stat(stock_data)
        
        # 计算加权综合评分
        total_score = (
            ma_alignment_score * self.config.ma_alignment_weight / 100.0
            + price_position_score * self.config.price_position_weight / 100.0
            + trend_strength_score * self.config.trend_strength_weight / 100.0
        )
        
        # 如果涨跌停次数评分较低，降低总评分
        if limit_stat_score < 50.0:
            total_score *= (limit_stat_score / 50.0)
        
        return total_score
    
    def _score_ma_alignment(
        self,
        close_price: float,
        ma5: float,
        ma10: float,
        ma20: float,
        ma60: float,
    ) -> float:
        """
        均线排列评分
        
        评分逻辑：
        - 多头排列（MA5 > MA10 > MA20 > MA60）：完美多头排列评分
        - 部分多头排列（MA5 > MA10 > MA20）：部分多头排列评分
        - 短期多头排列（MA5 > MA10）：短期多头排列评分
        - 空头排列（MA5 < MA10 < MA20 < MA60）：完美空头排列评分
        - 部分空头排列（MA5 < MA10 < MA20）：部分空头排列评分
        - 短期空头排列（MA5 < MA10）：短期空头排列评分
        - 其他情况：中性评分
        """
        if close_price > ma5 > ma10 > ma20 > ma60:
            return self.config.score_ma_perfect_bull  # 完美多头排列
        elif close_price > ma5 > ma10 > ma20:
            return self.config.score_ma_partial_bull  # 部分多头排列
        elif close_price > ma5 > ma10:
            return self.config.score_ma_short_bull  # 短期多头排列
        elif close_price < ma5 < ma10 < ma20 < ma60:
            return self.config.score_ma_perfect_bear  # 完美空头排列
        elif close_price < ma5 < ma10 < ma20:
            return self.config.score_ma_partial_bear  # 部分空头排列
        elif close_price < ma5 < ma10:
            return self.config.score_ma_short_bear  # 短期空头排列
        else:
            return self.config.score_ma_neutral  # 中性
    
    def _score_price_position(
        self,
        close_price: float,
        ma5: float,
        ma10: float,
        ma20: float,
        ma60: float,
    ) -> float:
        """
        价格位置评分
        
        评分逻辑：
        - 价格在所有均线之上：价格在所有均线之上评分
        - 价格在MA5、MA10、MA20之上：价格在3条均线之上评分
        - 价格在MA5、MA10之上：价格在2条均线之上评分
        - 价格在MA5之上：价格在1条均线之上评分
        - 价格在所有均线之下：价格在所有均线之下评分
        - 价格在MA5、MA10、MA20之下：价格在3条均线之下评分
        - 价格在MA5、MA10之下：价格在2条均线之下评分
        - 其他情况：中性评分
        """
        above_count = 0
        below_count = 0
        
        if close_price > ma5:
            above_count += 1
        else:
            below_count += 1
        
        if close_price > ma10:
            above_count += 1
        else:
            below_count += 1
        
        if close_price > ma20:
            above_count += 1
        else:
            below_count += 1
        
        if close_price > ma60:
            above_count += 1
        else:
            below_count += 1
        
        # 根据价格位置评分
        if above_count == 4:
            return self.config.score_price_all_above  # 价格在所有均线之上
        elif above_count == 3:
            return self.config.score_price_3_above  # 价格在3条均线之上
        elif above_count == 2:
            return self.config.score_price_2_above  # 价格在2条均线之上
        elif above_count == 1:
            return self.config.score_price_1_above  # 价格在1条均线之上
        elif below_count == 4:
            return self.config.score_price_all_below  # 价格在所有均线之下
        elif below_count == 3:
            return self.config.score_price_3_below  # 价格在3条均线之下
        elif below_count == 2:
            return self.config.score_price_2_below  # 价格在2条均线之下
        else:
            return self.config.score_price_neutral  # 中性
    
    def _score_trend_strength(
        self,
        close_price: float,
        ma5: float,
        ma10: float,
        ma20: float,
        ma60: float,
    ) -> float:
        """
        趋势强度评分
        
        评分逻辑：
        - 计算均线之间的距离（发散程度）
        - 计算价格相对于均线的距离
        - 综合评估趋势强度
        """
        # 计算均线发散程度
        ma_spread = abs(ma5 - ma20) / ma20 * 100
        
        # 计算价格相对于MA5的距离
        price_spread = abs(close_price - ma5) / ma5 * 100
        
        # 计算趋势强度评分
        # 均线发散程度越大，趋势越强
        # 价格距离MA5越大，趋势越强
        
        # 基础评分
        base_score = self.config.score_trend_base
        
        # 均线发散加分（最大值从配置读取）
        ma_spread_score = min(ma_spread * 2, self.config.score_trend_ma_spread_max)
        
        # 价格距离加分（最大值从配置读取）
        price_spread_score = min(price_spread * 1.5, self.config.score_trend_price_spread_max)
        
        # 判断趋势方向
        if close_price > ma5 and ma5 > ma20:
            # 上涨趋势，加分
            trend_score = base_score + ma_spread_score + price_spread_score
        elif close_price < ma5 and ma5 < ma20:
            # 下跌趋势，减分
            trend_score = base_score - ma_spread_score - price_spread_score
        else:
            # 中性趋势，基础评分
            trend_score = base_score
        
        # 确保评分在0-100之间
        return max(0.0, min(100.0, trend_score))
    
    def _score_limit_stat(self, stock_data: pd.DataFrame) -> float:
        """
        涨跌停次数评分
        
        评分逻辑：
        - 统计最近limit_stat_period天的涨跌停次数
        - 涨停次数越多，评分越高
        - 跌停次数越多，评分越低
        
        返回：评分（0-100）
        """
        # 检查数据是否为空
        if stock_data.empty:
            return 50.0
        
        # 获取最近limit_stat_period天的数据
        recent_df = stock_data.tail(self.config.limit_stat_period)
        
        if recent_df.empty:
            return 50.0
        
        # 计算涨跌幅
        if "pct_chg" not in recent_df.columns:
            return 50.0
        
        pct_chg = recent_df["pct_chg"]
        
        # 统计涨停次数（涨跌幅 >= 最大涨幅阈值）
        limit_up_count = sum(pct_chg >= self.config.max_up_threshold)
        
        # 统计跌停次数（涨跌幅 <= 最大跌幅阈值）
        limit_down_count = sum(pct_chg <= self.config.max_down_threshold)
        
        # 计算评分
        # 涨停次数越多，评分越高（每个涨停加10分，最多加50分）
        limit_up_score = min(limit_up_count * 10, 50.0)
        
        # 跌停次数越多，评分越低（每个跌停减10分，最多减50分）
        limit_down_score = max(-limit_down_count * 10, -50.0)
        
        # 基础评分50分
        base_score = 50.0
        
        # 总评分
        total_score = base_score + limit_up_score + limit_down_score
        
        # 确保评分在0-100之间
        return max(0.0, min(100.0, total_score))
    
    def filter_stock(self, daily_data: pd.Series, df: pd.DataFrame) -> bool:
        """
        筛选股票
        
        筛选逻辑：
        1. 市值区间筛选
        2. 股价区间筛选
        3. 涨跌停配置筛选
        
        返回：是否通过筛选
        """
        # 获取股价
        close_price = daily_data.get("close_price", 0)
        
        # 股价区间筛选
        if close_price < self.config.price_min or close_price > self.config.price_max:
            self.logger.debug(
                "股价不在区间内",
                close_price=close_price,
                price_min=self.config.price_min,
                price_max=self.config.price_max,
            )
            return False
        
        # 涨跌停配置筛选
        if self.config.limit_stat_period > 0:
            # 统计最近N天的涨跌停次数
            recent_df = df.tail(self.config.limit_stat_period)
            
            if not recent_df.empty:
                # 计算涨跌幅
                pct_chg = recent_df["pct_chg"]
                
                # 统计涨停次数（涨跌幅 >= 最大涨幅阈值）
                limit_up_count = sum(pct_chg >= self.config.max_up_threshold)
                
                # 统计跌停次数（涨跌幅 <= 最大跌幅阈值）
                limit_down_count = sum(pct_chg <= self.config.max_down_threshold)
                
                # 涨停次数筛选
                if limit_up_count < self.config.limit_up_min:
                    self.logger.debug(
                        "涨停次数不足",
                        limit_up_count=limit_up_count,
                        limit_up_min=self.config.limit_up_min,
                    )
                    return False
                
                # 跌停次数筛选
                if limit_down_count > self.config.limit_down_max:
                    self.logger.debug(
                        "跌停次数过多",
                        limit_down_count=limit_down_count,
                        limit_down_max=self.config.limit_down_max,
                    )
                    return False
        
        # 市值区间筛选（需要市值数据）
        # TODO: 如果数据中有市值字段，进行市值筛选
        
        return True
    
    def get_strategy_info(self) -> dict[str, Any]:
        """获取策略信息"""
        return {
            "strategy_name": self.strategy_name,
            "config": self.config.to_config_dict(),
        }