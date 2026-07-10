from typing import Any

import numpy as np
import pandas as pd

from src.core.config import config_loader
from src.core.logger import get_logger


class TechnicalIndicators:
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.config = config_loader.get("indicators", {})
    
    def add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        
        df = df.copy()
        
        df = self.add_ma(df)
        df = self.add_rsi(df)
        df = self.add_macd(df)
        df = self.add_bollinger_bands(df)
        df = self.add_volume_indicators(df)
        df = self.add_price_indicators(df)
        # 新增扩展指标
        df = self.add_adx(df)
        df = self.add_atr(df)
        df = self.add_historical_volatility(df)
        df = self.add_skewness(df)
        df = self.add_obv(df)
        df = self.add_volume_price_corr(df)
        df = self.add_new_high_low(df)
        df = self.add_path_indicators(df)
        
        return df
    
    def add_ma(self, df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
        if periods is None:
            periods = self.config.get("ma", {}).get("periods", [5, 10, 20, 60])
        
        df = df.copy()
        
        for period in periods:
            df[f"ma{period}"] = df["close_price"].rolling(window=period, min_periods=1).mean()
        
        return df
    
    def add_rsi(self, df: pd.DataFrame, period: int | None = None) -> pd.DataFrame:
        if period is None:
            period = self.config.get("rsi", {}).get("period", 14)
        
        df = df.copy()
        
        delta = df["close_price"].diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        
        return df
    
    def add_macd(
        self,
        df: pd.DataFrame,
        fast_period: int | None = None,
        slow_period: int | None = None,
        signal_period: int | None = None,
    ) -> pd.DataFrame:
        macd_config = self.config.get("macd", {})
        
        if fast_period is None:
            fast_period = macd_config.get("fast_period", 12)
        if slow_period is None:
            slow_period = macd_config.get("slow_period", 26)
        if signal_period is None:
            signal_period = macd_config.get("signal_period", 9)
        
        df = df.copy()
        
        ema_fast = df["close_price"].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df["close_price"].ewm(span=slow_period, adjust=False).mean()
        
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=signal_period, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        
        return df
    
    def add_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int | None = None,
        std_dev: float | None = None,
    ) -> pd.DataFrame:
        bb_config = self.config.get("bollinger_bands", {})
        
        if period is None:
            period = bb_config.get("period", 20)
        if std_dev is None:
            std_dev = bb_config.get("std_dev", 2.0)
        
        df = df.copy()
        
        df["bb_middle"] = df["close_price"].rolling(window=period, min_periods=1).mean()
        rolling_std = df["close_price"].rolling(window=period, min_periods=1).std()
        
        df["bb_upper"] = df["bb_middle"] + (rolling_std * std_dev)
        df["bb_lower"] = df["bb_middle"] - (rolling_std * std_dev)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        
        return df
    
    def add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df["volume_ma5"] = df["volume"].rolling(window=5, min_periods=1).mean()
        df["volume_ma10"] = df["volume"].rolling(window=10, min_periods=1).mean()
        
        df["volume_ratio"] = df["volume"] / df["volume_ma5"]
        
        return df
    
    def add_price_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df["price_change"] = df["close_price"].pct_change() * 100
        
        if "high_price" in df.columns and "low_price" in df.columns:
            df["high_low_pct"] = (df["high_price"] - df["low_price"]) / df["close_price"] * 100
        
        if "open_price" in df.columns:
            df["open_close_pct"] = abs(df["close_price"] - df["open_price"]) / df["open_price"] * 100
        
        return df
    
    # ==================== 新增扩展指标 ====================
    
    def add_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        ADX（平均趋向指数）：衡量趋势强度，不判断方向
        
        ADX > 25: 强趋势市
        ADX < 20: 震荡市/无趋势
        """
        df = df.copy()
        
        if len(df) < period + 1:
            df["adx"] = np.nan
            df["pdi"] = np.nan
            df["mdi"] = np.nan
            return df
        
        high = df["high_price"] if "high_price" in df.columns else df["close_price"]
        low = df["low_price"] if "low_price" in df.columns else df["close_price"]
        close = df["close_price"]
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        up_move = high.diff()
        down_move = -low.diff()
        
        pdm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        ndm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smoothed with Wilder's method (EMA-like)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        pdi = pd.Series(pdm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr * 100
        mdi = pd.Series(ndm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr * 100
        
        dx = abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan) * 100
        adx = dx.ewm(alpha=1/period, adjust=False).mean()
        
        df["adx"] = adx
        df["pdi"] = pdi
        df["mdi"] = mdi
        
        return df
    
    def add_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        ATR（平均真实波幅）：衡量价格波动幅度
        ATR/收盘价 = ATR百分比，用于跨股票比较
        """
        df = df.copy()
        
        if len(df) < 2:
            df["atr"] = np.nan
            df["atr_pct"] = np.nan
            return df
        
        high = df["high_price"] if "high_price" in df.columns else df["close_price"]
        low = df["low_price"] if "low_price" in df.columns else df["close_price"]
        close = df["close_price"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        df["atr"] = tr.ewm(alpha=1/period, adjust=False).mean()
        df["atr_pct"] = df["atr"] / df["close_price"] * 100
        
        return df
    
    def add_historical_volatility(
        self, df: pd.DataFrame, period: int = 20, annualize: bool = True
    ) -> pd.DataFrame:
        """
        历史波动率：收益率的标准差，年化处理
        
        - 20日年化波动率：衡量短期风险
        - 用于识别低波动/高波动股票
        """
        df = df.copy()
        
        if len(df) < period:
            df["hist_vol"] = np.nan
            return df
        
        ret = df["close_price"].pct_change()
        vol = ret.rolling(window=period, min_periods=5).std()
        
        if annualize:
            vol = vol * np.sqrt(252)  # 年化
        
        df["hist_vol"] = vol
        
        # 下行波动率：只计算下跌日的波动
        down_ret = ret.where(ret < 0, 0)
        down_vol = down_ret.rolling(window=period, min_periods=5).std()
        if annualize:
            down_vol = down_vol * np.sqrt(252)
        df["down_vol"] = down_vol
        
        return df
    
    def add_skewness(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        收益偏度：收益分布的不对称性
        
        - 正偏度：上涨幅度大、下跌幅度小（好）
        - 负偏度：下跌幅度大、上涨幅度小（差）
        """
        df = df.copy()
        
        if len(df) < period:
            df["ret_skew"] = np.nan
            return df
        
        ret = df["close_price"].pct_change()
        df["ret_skew"] = ret.rolling(window=period, min_periods=10).skew()
        
        return df
    
    def add_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        OBV（能量潮）：累积成交量指标
        
        - OBV上升 = 量价配合良好
        - OBV与价格背离 = 趋势可能反转
        """
        df = df.copy()
        
        if "volume" not in df.columns:
            df["obv"] = np.nan
            df["obv_ma5"] = np.nan
            return df
        
        close = df["close_price"]
        volume = df["volume"]
        
        # 价格涨则加成交量，跌则减
        direction = np.where(close.diff() > 0, 1, np.where(close.diff() < 0, -1, 0))
        obv = (direction * volume).cumsum()
        
        df["obv"] = obv
        df["obv_ma5"] = obv.rolling(window=5, min_periods=1).mean()
        
        return df
    
    def add_volume_price_corr(self, df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        """
        量价相关性：价格变化与成交量变化的相关性
        
        - 正相关：量价齐升/量价齐跌（趋势确认）
        - 负相关：量价背离（可能反转）
        """
        df = df.copy()
        
        if len(df) < period or "volume" not in df.columns:
            df["vp_corr"] = np.nan
            return df
        
        price_chg = df["close_price"].pct_change()
        vol_chg = df["volume"].pct_change()
        
        df["vp_corr"] = price_chg.rolling(window=period, min_periods=5).corr(vol_chg)
        
        return df
    
    def add_new_high_low(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        新高新低比：
        - 当前收盘价 / N日最高价 → 距离新高的距离
        - (当前价 - N日最低价) / (N日最高价 - N日最低价) → 相对位置
        """
        df = df.copy()
        
        if len(df) < period:
            df["high_ratio"] = np.nan
            df["price_position"] = np.nan
            return df
        
        close = df["close_price"]
        high_n = close.rolling(window=period, min_periods=1).max()
        low_n = close.rolling(window=period, min_periods=1).min()
        
        df["high_ratio"] = close / high_n.replace(0, np.nan)  # 1.0 = 创N日新高
        df["price_position"] = (close - low_n) / (high_n - low_n).replace(0, np.nan)  # 0~1
        
        return df
    
    def add_path_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        路径指标：
        - 最大回撤（从N日最高点）
        - 连续涨跌天数
        """
        df = df.copy()
        
        if len(df) < 5:
            df["drawdown_20d"] = np.nan
            df["consecutive_up"] = 0
            df["consecutive_down"] = 0
            return df
        
        close = df["close_price"]
        
        # 20日最大回撤（从区间最高点计算）
        high_20 = close.rolling(window=20, min_periods=5).max()
        df["drawdown_20d"] = (close - high_20) / high_20.replace(0, np.nan) * 100
        
        # 连续涨跌天数
        pct = close.pct_change()
        consecutive_up = []
        consecutive_down = []
        up_count = 0
        down_count = 0
        
        for chg in pct:
            if pd.isna(chg):
                up_count = 0
                down_count = 0
            elif chg > 0:
                up_count += 1
                down_count = 0
            elif chg < 0:
                down_count += 1
                up_count = 0
            else:
                up_count = 0
                down_count = 0
            consecutive_up.append(up_count)
            consecutive_down.append(down_count)
        
        df["consecutive_up"] = consecutive_up
        df["consecutive_down"] = consecutive_down
        
        return df