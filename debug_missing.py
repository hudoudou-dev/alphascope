#!/usr/bin/env python3
"""诊断中际旭创、新易盛、天孚通信为什么被 filter_stock 过滤掉"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 清除配置缓存
import src.core.config as _cfg
_cfg.config_loader._config = None

from src.strategy.selection_strategy import SelectionStrategy, SelectionConfig
from src.indicators.technical_indicators import TechnicalIndicators

TARGET_CODES = {
    "300308": "中际旭创",
    "300502": "新易盛", 
    "300394": "天孚通信",
}

RAW_PATH = os.path.join(os.path.dirname(__file__), "data", "raw")

config = SelectionConfig.from_config()
# 手动覆盖权重
config.trend_weight = 35.0
config.volatility_weight = 10.0
strategy = SelectionStrategy(config)

print("=" * 80)
print("  中际旭创/新易盛/天孚通信 — filter_stock 拦截诊断")
print("=" * 80)
print(f"\n当前 filter_stock 参数：")
print(f"  price_min = {config.price_min}")
print(f"  price_max = {config.price_max}")
print(f"  market_cap_min = {config.market_cap_min} 亿元")
print(f"  market_cap_max = {config.market_cap_max} 亿元")
print(f"  limit_up_min = {config.limit_up_min}")
print(f"  limit_down_max = {config.limit_down_max}")
print(f"  limit_stat_period = {config.limit_stat_period} 天")
print(f"  max_up_threshold = {config.max_up_threshold}%")
print(f"  max_down_threshold = {config.max_down_threshold}%")
print(f"  enable_risk_control = {config.enable_risk_control}")
print(f"  enable_st_filter = {config.enable_st_filter}")
print(f"  enable_limit_filter = {config.enable_limit_filter}")

print("\n" + "-" * 80)

for pure_code, stock_name in TARGET_CODES.items():
    print(f"\n{'='*60}")
    print(f"  📊 {pure_code} {stock_name}")
    print(f"{'='*60}")
    
    # 找文件
    matching = [f for f in os.listdir(RAW_PATH) if f.startswith(pure_code) and f.endswith(".parquet")]
    if not matching:
        print(f"  ❌ 数据文件不存在！")
        continue
    
    filepath = os.path.join(RAW_PATH, matching[0])
    df = pd.read_parquet(filepath)
    df["date"] = pd.to_datetime(df["date"])
    
    # 基本信息
    latest = df.iloc[-1]
    close_price = latest.get("close_price", 0)
    
    print(f"\n  最新行情（{df['date'].iloc[-1].strftime('%Y-%m-%d')}）：")
    print(f"    close={close_price}")
    print(f"    volume={latest.get('volume', 'N/A')}")
    
    # 检查总市值
    market_cap = latest.get("total_mv", None)
    if market_cap is not None and not pd.isna(market_cap):
        cap_yi = float(market_cap) / 1e8
        print(f"    total_mv={float(market_cap):.0f} (≈{cap_yi:.1f}亿元)")
    else:
        print(f"    total_mv=缺失")
    
    # --- 逐步检查 filter_stock 的每个条件 ---
    print(f"\n  🔍 filter_stock 逐步检查：")
    
    # 条件1：股价区间
    if close_price < config.price_min or close_price > config.price_max:
        print(f"    ❌ 股价筛选：close={close_price} 不在 [{config.price_min}, {config.price_max}]")
    else:
        print(f"    ✅ 股价筛选：close={close_price} 在 [{config.price_min}, {config.price_max}]")
    
    # 条件2：涨跌停配置
    # 先 prepare 数据以获取 pct_chg
    df_prepared = strategy.prepare(df)
    df_recent = df_prepared.tail(config.limit_stat_period)
    
    if not df_recent.empty and "pct_chg" in df_recent.columns:
        pct_chg = df_recent["pct_chg"]
        limit_up_count = int(sum(pct_chg >= config.max_up_threshold))
        limit_down_count = int(sum(pct_chg <= config.max_down_threshold))
        print(f"    涨停次数（{config.limit_stat_period}天）= {limit_up_count}，最小要求 = {config.limit_up_min}")
        print(f"    跌停次数（{config.limit_stat_period}天）= {limit_down_count}，最大允许 = {config.limit_down_max}")
        
        if limit_up_count < config.limit_up_min:
            print(f"    ❌ 涨停次数不足")
        elif limit_down_count > config.limit_down_max:
            print(f"    ❌ 跌停次数过多")
        else:
            print(f"    ✅ 涨跌停筛选通过")
    else:
        print(f"    ⚠️  pct_chg 数据缺失，跳过涨跌停筛选")
    
    # 条件3：市值区间
    if market_cap is not None and not pd.isna(market_cap):
        cap_yi = float(market_cap) / 1e8
        if cap_yi < config.market_cap_min or cap_yi > config.market_cap_max:
            print(f"    ❌ 市值筛选：{cap_yi:.1f}亿元 不在 [{config.market_cap_min}, {config.market_cap_max}]")
        else:
            print(f"    ✅ 市值筛选：{cap_yi:.1f}亿元 在 [{config.market_cap_min}, {config.market_cap_max}]")
    else:
        print(f"    ✅ 市值筛选：无市值数据，跳过")
    
    # 条件4：风控
    if config.enable_risk_control:
        code_val = latest.get("code", pure_code)
        pct_val = df_prepared.iloc[-1].get("pct_chg", None)
        print(f"    当日涨跌幅 = {pct_val if pct_val is not None else 'N/A'}")
        
        # 检查是否当日涨停（涨跌幅 >= max_up_threshold）
        if pct_val is not None and not pd.isna(pct_val):
            if float(pct_val) >= config.max_up_threshold and config.enable_limit_filter:
                print(f"    ❌ 风控拦截：当日涨停（{float(pct_val):.2f}% >= {config.max_up_threshold}%），不可买入")
            else:
                print(f"    ✅ 当日非涨停/涨停过滤关闭")
        else:
            print(f"    ⚠️  无涨跌幅数据")
        
        # 检查ST
        stock_name_in_data = ""
        if "name" in df.columns:
            stock_name_in_data = str(df.iloc[0].get("name", ""))
        is_st = "ST" in stock_name_in_data or "*ST" in stock_name_in_data
        if is_st and config.enable_st_filter:
            print(f"    ❌ ST股过滤：{stock_name_in_data}")
        else:
            print(f"    ✅ 非ST股/ST过滤关闭")
    else:
        print(f"    ⚠️  风控未启用")
    
    # --- 最终 filter_stock 结果 ---
    result = strategy.filter_stock(df_prepared.iloc[-1], df_prepared)
    print(f"\n  📋 filter_stock 最终结果：{'✅ 通过' if result else '❌ 未通过'}")
    
    # 如果通过了，计算因子得分
    if result:
        df_recent_score = df_prepared.tail(config.limit_stat_period)
        score = strategy.score_stock(pure_code, df_recent_score)
        
        # 获取子策略分项得分
        sub_scores = strategy.get_last_detail_scores()
        
        # 获取详细数据
        lat = df_prepared.iloc[-1]
        rsi = lat.get("rsi", None)
        macd = lat.get("macd", None)
        macd_sig = lat.get("macd_signal", None)
        vol_ratio = lat.get("volume_ratio", None)
        ma5, ma10, ma20, ma60 = lat.get("ma5"), lat.get("ma10"), lat.get("ma20"), lat.get("ma60")
        adx = lat.get("adx", None)
        hist_vol = lat.get("hist_vol", None)
        vp_corr = lat.get("vp_corr", None)
        
        # 20日涨幅
        if len(df_prepared) >= 20:
            ret_20d = (close_price - df_prepared["close_price"].iloc[-20]) / df_prepared["close_price"].iloc[-20] * 100
        else:
            ret_20d = None
        
        print(f"\n  📊 因子打分明细：")
        print(f"    MA: close={close_price}, MA5={ma5}, MA10={ma10}, MA20={ma20}, MA60={ma60}")
        print(f"    MACD={macd}, Signal={macd_sig} → {'金叉' if (macd is not None and macd_sig is not None and macd > macd_sig) else '死叉' if (macd is not None and macd_sig is not None) else 'N/A'}")
        if ret_20d is not None:
            print(f"    20日涨幅 = {ret_20d:.1f}%")
        print(f"    RSI={float(rsi):.1f}" if rsi is not None and not pd.isna(rsi) else "    RSI=N/A")
        print(f"    量比={float(vol_ratio):.2f}" if vol_ratio is not None and not pd.isna(vol_ratio) else "    量比=N/A")
        if adx is not None and not pd.isna(adx):
            print(f"    ADX={float(adx):.1f}")
        if hist_vol is not None and not pd.isna(hist_vol):
            print(f"    历史波动率={float(hist_vol):.2f}")
        if vp_corr is not None and not pd.isna(vp_corr):
            print(f"    量价相关性={float(vp_corr):.2f}")
        
        # 计算BB位置
        bb_upper = lat.get("bb_upper", None)
        bb_lower = lat.get("bb_lower", None)
        if bb_upper is not None and bb_lower is not None:
            bb_range = float(bb_upper) - float(bb_lower)
            if bb_range > 0:
                bb_pos = (close_price - float(bb_lower)) / bb_range * 100
                print(f"    BB位置={bb_pos:.1f}%")
        
        print(f"\n  📊 子策略分项得分：")
        for sname, sscore in sub_scores.items():
            bar = "█" * int(sscore / 2)
            print(f"    {sname:22s}: {sscore:5.1f}  {bar}")
        print(f"\n  🎯 综合评分 = {score:.2f}")
        
        # 检查是否超过 min_score_threshold
        print(f"  阈值 = {config.min_score_threshold} → {'✅ 通过' if score >= config.min_score_threshold else '❌ 未通过'}")
    else:
        print(f"\n  ⚠️  该股票被 filter_stock 拦截，无法进入评分阶段")
        print(f"  → 需要调整 filter_stock 参数才能让此类股票进入选股池")

print("\n" + "=" * 80)
print("  对比：当前16只已通过筛选的股票")
print("=" * 80)

all_files = [f for f in os.listdir(RAW_PATH) if f.endswith(".parquet")]
for f in sorted(all_files):
    filepath = os.path.join(RAW_PATH, f)
    df = pd.read_parquet(filepath)
    df["date"] = pd.to_datetime(df["date"])
    df = strategy.prepare(df)
    latest = df.iloc[-1]
    result = strategy.filter_stock(latest, df)
    status = "✅" if result else "❌"
    code = f.split(".")[0]
    name = ""
    if "name" in df.columns:
        name = str(df.iloc[0].get("name", ""))
    close = latest.get("close_price", 0)
    cap = latest.get("total_mv", None)
    cap_str = f"{float(cap)/1e8:.0f}亿" if cap is not None and not pd.isna(cap) else "N/A"
    print(f"  {status} {code} {name:8s} close={close:8.2f} 市值={cap_str:>8s}")
