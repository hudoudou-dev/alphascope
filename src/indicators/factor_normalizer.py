"""
横截面标准化器（Cross-sectional Normalizer）

将「单只股票视角」的因子/子策略原始得分，转换为「全市场横截面视角」下
0-100 的相对得分，使选股结果在不同市场环境下具有可比性。

支持两种归一化方法：
- zscore：横截面标准化（均值0/标准差1）后线性映射到 [0,100]
- rank：横截面百分位排名（0%~100%）映射到 [0,100]

默认关闭，仅当 strategy.cross_sectional.enabled=true 时由 SelectionStrategy 调用。
"""

from typing import Literal

import numpy as np


class FactorNormalizer:
    def __init__(
        self,
        method: Literal["zscore", "rank"] = "zscore",
        clip: float = 3.0,
        target_low: float = 0.0,
        target_high: float = 100.0,
    ):
        self.method = method
        self.clip = clip
        self.target_low = target_low
        self.target_high = target_high
        # 每个因子的横截面统计量：{因子名: {mean, std} | {sorted: ndarray}}
        self._stats: dict[str, dict] = {}

    def fit(self, universe: dict[str, dict[str, float]]) -> None:
        """根据全市场 universe（code -> {因子: 原始得分}）拟合横截面分布。"""
        self._stats = {}
        if not universe:
            return

        factors: set[str] = set()
        for scores in universe.values():
            factors.update(scores.keys())

        for factor in factors:
            vals = np.array(
                [s.get(factor, np.nan) for s in universe.values()], dtype=float
            )
            vals = vals[~np.isnan(vals)]
            if len(vals) == 0:
                continue
            if self.method == "zscore":
                self._stats[factor] = {
                    "mean": float(vals.mean()),
                    "std": float(vals.std(ddof=0)) or 1.0,
                }
            else:  # rank
                self._stats[factor] = {"sorted": np.sort(vals)}

    def transform(self, factor: str, raw: float) -> float:
        """将单个原始得分转换为横截面归一化得分（0-100）。缺失/未拟合返回中性 50。"""
        if factor not in self._stats or raw is None or (isinstance(raw, float) and np.isnan(raw)):
            return 50.0

        if self.method == "zscore":
            st = self._stats[factor]
            std = st["std"] or 1.0
            z = (raw - st["mean"]) / std
            z = float(np.clip(z, -self.clip, self.clip))
            norm = (z + self.clip) / (2 * self.clip)
        else:  # rank 百分位
            sorted_vals = self._stats[factor]["sorted"]
            pct = float((sorted_vals < raw).mean())  # 低于该值的比例
            norm = pct

        return self.target_low + norm * (self.target_high - self.target_low)

    def normalize_universe(
        self, universe: dict[str, dict[str, float]]
    ) -> dict[str, dict[str, float]]:
        """对全市场所有股票的各因子原始得分做横截面归一化，返回同结构字典。"""
        self.fit(universe)
        out: dict[str, dict[str, float]] = {}
        for code, scores in universe.items():
            out[code] = {f: self.transform(f, v) for f, v in scores.items()}
        return out
