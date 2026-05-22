import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Any

from src.backtest.backtest_engine import BacktestEngine, BacktestResult
from src.strategy.base_strategy import BaseStrategy
from src.indicators.technical_indicators import TechnicalIndicators
from src.core.config import config_loader
from src.core.logger import get_logger


st.set_page_config(
    page_title="AlphaScope - A股量化回测平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
    .main {
        background-color: #1a1a2e;
        color: #eaeaea;
    }
    .stApp {
        background-color: #1a1a2e;
    }
    .stSidebar {
        background-color: #16213e;
    }
    .stMetric {
        background-color: #0f3460;
        padding: 20px;
        border-radius: 10px;
    }
    .stMetric label {
        color: #e94560 !important;
        font-size: 14px !important;
    }
    .stMetric value {
        color: #eaeaea !important;
        font-size: 28px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


logger = get_logger("WebApp")
web_config = config_loader.get("web", {}).get("control_panel", {})


class SimpleMAStrategy(BaseStrategy):
    
    def __init__(self, ma_short: int | None = None, ma_long: int | None = None):
        ma_config = config_loader.get("strategy", {}).get("ma_strategy", {})
        
        self.ma_short = ma_short or ma_config.get("ma_short", 5)
        self.ma_long = ma_long or ma_config.get("ma_long", 20)
        
        super().__init__(strategy_name="SimpleMAStrategy")
        
        self.score_trend_up = ma_config.get("score_trend_up", 75.0)
        self.score_trend_up_weak = ma_config.get("score_trend_up_weak", 60.0)
        self.score_trend_down = ma_config.get("score_trend_down", 25.0)
        self.score_neutral = ma_config.get("score_neutral", 50.0)
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        df = indicators.add_ma(df, periods=[self.ma_short, self.ma_long])
        return df
    
    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        if self._prepared_data is None:
            return self.score_neutral
        
        code_df = self._prepared_data[self._prepared_data["code"] == code]
        
        if code_df.empty or len(code_df) < self.ma_long:
            return self.score_neutral
        
        latest = code_df.iloc[-1]
        score = self.score_neutral
        
        ma_short = latest.get(f"ma{self.ma_short}")
        ma_long = latest.get(f"ma{self.ma_long}")
        close_price = latest.get("close_price")
        
        if ma_short and ma_long and close_price:
            if close_price > ma_short > ma_long:
                score = self.score_trend_up
            elif close_price > ma_short:
                score = self.score_trend_up_weak
            elif close_price < ma_short < ma_long:
                score = self.score_trend_down
        
        return score


def generate_sample_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    
    data = []
    for i, date in enumerate(dates):
        base_price = 10.0 + i * 0.05 + np.sin(i / 10) * 0.5
        data.append({
            "date": date,
            "open_price": base_price,
            "high_price": base_price + 0.3,
            "low_price": base_price - 0.3,
            "close_price": base_price + 0.1,
            "volume": 1000000.0 + np.random.randint(-100000, 100000),
            "amount": 10000000.0 + np.random.randint(-1000000, 1000000),
            "code": "600000.SH",
        })
    
    return pd.DataFrame(data)


def render_control_panel() -> dict[str, Any]:
    st.sidebar.title("🎛️ 控制面板")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("💰 资金配置")
    initial_cash_config = web_config.get("initial_cash", {})
    initial_cash = st.sidebar.number_input(
        "初始资金",
        min_value=initial_cash_config.get("min_value", 10000),
        max_value=initial_cash_config.get("max_value", 100000000),
        value=initial_cash_config.get("default_value", 1000000),
        step=initial_cash_config.get("step", 10000),
    )
    
    st.sidebar.subheader("📊 策略参数")
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["SimpleMAStrategy", "RSIStrategy", "MACDStrategy"],
    )
    
    ma_short_config = web_config.get("ma_short", {})
    ma_short = st.sidebar.slider(
        "短期均线",
        min_value=ma_short_config.get("min_value", 3),
        max_value=ma_short_config.get("max_value", 20),
        value=ma_short_config.get("default_value", 5),
    )
    
    ma_long_config = web_config.get("ma_long", {})
    ma_long = st.sidebar.slider(
        "长期均线",
        min_value=ma_long_config.get("min_value", 10),
        max_value=ma_long_config.get("max_value", 60),
        value=ma_long_config.get("default_value", 20),
    )
    
    st.sidebar.subheader("🛡️ 风控参数")
    stop_loss_config = web_config.get("stop_loss", {})
    stop_loss = st.sidebar.slider(
        "止损线 (%)",
        min_value=stop_loss_config.get("min_value", -20),
        max_value=stop_loss_config.get("max_value", -1),
        value=stop_loss_config.get("default_value", -8),
    )
    
    take_profit_config = web_config.get("take_profit", {})
    take_profit = st.sidebar.slider(
        "止盈线 (%)",
        min_value=take_profit_config.get("min_value", 5),
        max_value=take_profit_config.get("max_value", 50),
        value=take_profit_config.get("default_value", 20),
    )
    
    st.sidebar.subheader("📅 回测区间")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        default_start = web_config.get("default_start_date", "2024-01-01")
        start_date = st.date_input("开始日期", value=datetime.strptime(default_start, "%Y-%m-%d"))
    with col2:
        default_end = web_config.get("default_end_date", "2024-03-31")
        end_date = st.date_input("结束日期", value=datetime.strptime(default_end, "%Y-%m-%d"))
    
    st.sidebar.markdown("---")
    run_backtest = st.sidebar.button("🚀 启动回测", type="primary", use_container_width=True)
    
    return {
        "initial_cash": initial_cash,
        "strategy_name": strategy_name,
        "ma_short": ma_short,
        "ma_long": ma_long,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "start_date": start_date,
        "end_date": end_date,
        "run_backtest": run_backtest,
    }


def render_metrics_cards(result: BacktestResult) -> None:
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            label="总收益率",
            value=f"{result.total_return:.2f}%",
            delta=f"{result.total_return:.2f}%",
        )
    
    with col2:
        st.metric(
            label="年化收益率",
            value=f"{result.annual_return:.2f}%",
            delta=f"{result.annual_return:.2f}%",
        )
    
    with col3:
        st.metric(
            label="最大回撤",
            value=f"{result.max_drawdown:.2f}%",
            delta=f"-{result.max_drawdown:.2f}%",
            delta_color="inverse",
        )
    
    with col4:
        st.metric(
            label="夏普比率",
            value=f"{result.sharpe_ratio:.2f}",
        )
    
    with col5:
        st.metric(
            label="总交易次数",
            value=f"{result.total_trades}",
        )
    
    with col6:
        st.metric(
            label="胜率",
            value=f"{result.win_rate:.1f}%",
        )


def render_equity_chart(result: BacktestResult) -> None:
    st.subheader("📈 资产净值与回撤")
    
    if not result.portfolio_states:
        st.warning("暂无数据")
        return
    
    df = pd.DataFrame([state.to_dict() for state in result.portfolio_states])
    
    df["date"] = pd.to_datetime(df["date"])
    df["normalized_value"] = df["total_value"] / df["total_value"].iloc[0]
    
    df["peak"] = df["total_value"].cummax()
    df["drawdown"] = (df["total_value"] - df["peak"]) / df["peak"] * 100
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.line_chart(
            df.set_index("date")[["normalized_value"]],
            use_container_width=True,
        )
    
    with col2:
        st.area_chart(
            df.set_index("date")[["drawdown"]],
            use_container_width=True,
        )


def render_kline_chart(result: BacktestResult, stock_data: pd.DataFrame) -> None:
    st.subheader("📊 K线图与交易信号")
    
    if stock_data.empty:
        st.warning("暂无数据")
        return
    
    stock_code = st.selectbox(
        "选择股票",
        stock_data["code"].unique().tolist(),
    )
    
    stock_df = stock_data[stock_data["code"] == stock_code].copy()
    
    if stock_df.empty:
        st.warning("该股票无数据")
        return
    
    transactions = [t for t in result.transactions if t.code == stock_code]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        chart_data = stock_df[["date", "open_price", "high_price", "low_price", "close_price"]].copy()
        chart_data = chart_data.set_index("date")
        st.line_chart(chart_data, use_container_width=True)
    
    with col2:
        if transactions:
            st.write("**交易记录**")
            for trans in transactions[-5:]:
                st.write(f"{trans.date.strftime('%Y-%m-%d')}")
                st.write(f"{trans.action} {trans.shares}股 @ {trans.price:.2f}")
                st.write("---")


def render_transaction_table(result: BacktestResult) -> None:
    st.subheader("📋 交易明细")
    
    if not result.transactions:
        st.info("当前参数未触发任何交易信号")
        return
    
    df = pd.DataFrame([trans.to_dict() for trans in result.transactions])
    
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    
    st.dataframe(
        df[["date", "code", "action", "price", "shares", "commission", "amount"]],
        use_container_width=True,
        hide_index=True,
    )


def render_portfolio_table(result: BacktestResult) -> None:
    st.subheader("📊 每日资产状态")
    
    if not result.portfolio_states:
        st.info("暂无数据")
        return
    
    records = []
    for state in result.portfolio_states:
        records.append({
            "date": state.date.strftime("%Y-%m-%d"),
            "capital": f"{state.capital:,.2f}",
            "positions_value": f"{state.positions_value:,.2f}",
            "total_value": f"{state.total_value:,.2f}",
        })
    
    df = pd.DataFrame(records)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 导出 CSV",
        data=csv,
        file_name="portfolio_states.csv",
        mime="text/csv",
    )


def main():
    st.title("📈 AlphaScope - A股量化回测平台")
    st.markdown("---")
    
    params = render_control_panel()
    
    if params["run_backtest"]:
        with st.spinner("正在运行回测..."):
            try:
                stock_data = generate_sample_data(
                    pd.to_datetime(params["start_date"]),
                    pd.to_datetime(params["end_date"]),
                )
                
                strategy = SimpleMAStrategy(
                    ma_short=params["ma_short"],
                    ma_long=params["ma_long"],
                )
                strategy.stop_loss_pct = params["stop_loss"]
                strategy.take_profit_pct = params["take_profit"]
                
                engine = BacktestEngine(
                    strategy=strategy,
                    initial_cash=params["initial_cash"],
                )
                
                result = engine.run(stock_data)
                
                st.session_state["result"] = result
                st.session_state["stock_data"] = stock_data
                
                st.success("回测完成！")
                
            except Exception as e:
                st.error(f"回测失败: {str(e)}")
                logger.error("Backtest failed", error=str(e))
    
    if "result" in st.session_state:
        result = st.session_state["result"]
        stock_data = st.session_state.get("stock_data", pd.DataFrame())
        
        st.markdown("---")
        render_metrics_cards(result)
        
        st.markdown("---")
        tab1, tab2, tab3 = st.tabs(["📈 资产曲线", "📊 K线图", "📋 数据明细"])
        
        with tab1:
            render_equity_chart(result)
        
        with tab2:
            render_kline_chart(result, stock_data)
        
        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                render_transaction_table(result)
            with col2:
                render_portfolio_table(result)


if __name__ == "__main__":
    main()