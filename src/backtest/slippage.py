from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SlippageResult:
    original_price: float
    slippage: float
    adjusted_price: float
    
    @property
    def slippage_rate(self) -> float:
        if self.original_price == 0:
            return 0.0
        return self.slippage / self.original_price


class SlippageModel(ABC):
    
    @abstractmethod
    def calculate(self, price: float, volume: int = 0) -> SlippageResult:
        pass
    
    def calculate_buy_slippage(self, price: float, volume: int = 0) -> float:
        return self.calculate(price, volume).slippage
    
    def calculate_sell_slippage(self, price: float, volume: int = 0) -> float:
        return self.calculate(price, volume).slippage


class FixedSlippageModel(SlippageModel):
    
    def __init__(self, slippage_rate: float = 0.001):
        self.slippage_rate = slippage_rate
    
    def calculate(self, price: float, volume: int = 0) -> SlippageResult:
        slippage = price * self.slippage_rate
        return SlippageResult(
            original_price=price,
            slippage=slippage,
            adjusted_price=price + slippage,
        )


class PercentageSlippageModel(SlippageModel):
    
    def __init__(self, slippage_rate: float = 0.001):
        self.slippage_rate = slippage_rate
    
    def calculate(self, price: float, volume: int = 0) -> SlippageResult:
        slippage = price * self.slippage_rate
        return SlippageResult(
            original_price=price,
            slippage=slippage,
            adjusted_price=price + slippage,
        )


class VolumeBasedSlippageModel(SlippageModel):
    
    def __init__(
        self,
        base_slippage_rate: float = 0.0005,
        volume_sensitivity: float = 0.0001,
        max_slippage_rate: float = 0.01,
    ):
        self.base_slippage_rate = base_slippage_rate
        self.volume_sensitivity = volume_sensitivity
        self.max_slippage_rate = max_slippage_rate
    
    def calculate(self, price: float, volume: int = 0) -> SlippageResult:
        slippage_rate = min(
            self.base_slippage_rate + self.volume_sensitivity * (volume / 10000),
            self.max_slippage_rate,
        )
        slippage = price * slippage_rate
        return SlippageResult(
            original_price=price,
            slippage=slippage,
            adjusted_price=price + slippage,
        )