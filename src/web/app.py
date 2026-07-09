"""
AlphaScope 统一Web平台

本模块提供完整的Web界面，包括：
- 数据下载与同步（支持自动数据源切换）
- 本地库存管理
- K线图可视化与验真
- 回测分析（支持真实数据和合成数据）

使用示例：
    streamlit run src/web/app.py
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.backtest.backtest_engine import BacktestEngine, BacktestResult
from src.core.config import config_loader
from src.core.logger import get_logger
from src.data.providers.akshare_provider import AKShareProvider
from src.data.providers.baostock_provider import BaoStockProvider
from src.data.providers.tushare_provider import TushareProvider
from src.indicators.technical_indicators import TechnicalIndicators
from src.web.utils import normalize_stock_code


logger = get_logger("WebAppUnified")


st.set_page_config(
    page_title="AlphaScope - A股量化选股与回测平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
    /* Dark主题样式 */
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stApp {
        background-color: #0e1117;
    }
    .stSidebar {
        background-color: #262730;
    }
    .stMetric {
        background-color: #1a1d29;
        padding: 20px;
        border-radius: 10px;
    }
    .stMetric label {
        color: #ff4b6e !important;
        font-size: 14px !important;
    }
    .stMetric value {
        color: #ffffff !important;
        font-size: 28px !important;
    }
    /* 确保所有文本都有足够的对比度 */
    .stMarkdown {
        color: #ffffff !important;
    }
    .stText {
        color: #ffffff !important;
    }
    .stHeader {
        color: #ffffff !important;
    }
    /* 确保按钮和输入框的对比度 */
    .stButton button {
        color: #ffffff !important;
    }
    .stTextInput input {
        color: #ffffff !important;
        background-color: #1a1d29 !important;
    }
    .stSelectbox select {
        color: #ffffff !important;
        background-color: #1a1d29 !important;
    }
    /* 确保数据表格的对比度 */
    .stDataFrame {
        color: #ffffff !important;
    }
    /* 确保进度条的对比度 */
    .stProgress > div > div {
        background-color: #ff4b6e !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


@dataclass
class DownloadTask:
    code: str
    start_date: datetime
    end_date: datetime
    adjust: str = "qfq"
    status: str = "pending"
    error: str | None = None
    rows: int = 0
    provider: str = ""


@dataclass
class DownloadProgress:
    total: int = 0
    completed: int = 0
    failed: int = 0
    current_code: str = ""
    current_provider: str = ""
    start_time: datetime | None = None
    logs: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def progress_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed + self.failed) / self.total * 100
    
    @property
    def eta(self) -> str:
        if self.start_time is None or self.completed == 0:
            return "计算中..."
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time = elapsed / self.completed
        remaining = (self.total - self.completed - self.failed) * avg_time
        
        if remaining < 60:
            return f"{int(remaining)}秒"
        elif remaining < 3600:
            return f"{int(remaining / 60)}分钟"
        else:
            return f"{int(remaining / 3600)}小时"


class AutoSwitchProvider:
    
    def __init__(self):
        self.providers = {
            "akshare": AKShareProvider,
            "baostock": BaoStockProvider,
            "tushare": TushareProvider,
        }
        self.provider_order = ["akshare", "baostock", "tushare"]
        self.current_provider_index = 0
        self.logger = get_logger("AutoSwitchProvider")
    
    def get_provider(self, provider_name: str | None = None):
        if provider_name:
            return self.providers.get(provider_name, AKShareProvider)()
        
        provider_name = self.provider_order[self.current_provider_index]
        return self.providers[provider_name]()
    
    def switch_provider(self) -> str | None:
        if self.current_provider_index < len(self.provider_order) - 1:
            self.current_provider_index += 1
            next_provider = self.provider_order[self.current_provider_index]
            self.logger.info(f"切换数据源到: {next_provider}")
            return next_provider
        return None
    
    def reset(self):
        self.current_provider_index = 0


class DownloadManager:
    
    def __init__(self):
        self.progress = DownloadProgress()
        self.is_running = False
        self._lock = threading.Lock()
        self.provider_manager = AutoSwitchProvider()
    
    def start_download(
        self,
        codes: list[str],
        start_date: datetime,
        end_date: datetime,
        adjust: str,
    ):
        with self._lock:
            if self.is_running:
                return
            
            self.is_running = True
            self.progress = DownloadProgress(
                total=len(codes),
                start_time=datetime.now(),
            )
            self.provider_manager.reset()
        
        thread = threading.Thread(
            target=self._download_worker,
            args=(codes, start_date, end_date, adjust),
            daemon=True,
        )
        thread.start()
    
    def _download_worker(
        self,
        codes: list[str],
        start_date: datetime,
        end_date: datetime,
        adjust: str,
    ):
        try:
            for code in codes:
                if not self.is_running:
                    break
                
                with self._lock:
                    self.progress.current_code = code
                
                success = False
                retry_count = 0
                max_retries = 3
                
                while not success and retry_count < max_retries:
                    try:
                        provider_name = self.provider_manager.provider_order[
                            self.provider_manager.current_provider_index
                        ]
                        
                        with self._lock:
                            self.progress.current_provider = provider_name
                        
                        provider = self.provider_manager.get_provider()
                        
                        df = provider.download_and_save(
                            code=code,
                            start_date=start_date,
                            end_date=end_date,
                            adjust=adjust,
                        )
                        
                        if not df.empty:
                            with self._lock:
                                self.progress.completed += 1
                                self.progress.logs.append(
                                    f"[SUCCESS] {code} 下载成功（{provider_name}），共导入 {len(df)} 行数据"
                                )
                            success = True
                        else:
                            raise Exception("数据为空")
                    
                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e)
                        
                        # 记录错误日志
                        with self._lock:
                            self.progress.logs.append(
                                f"[ERROR] {code} 下载失败（尝试 {retry_count}/{max_retries}）: {error_msg[:100]}"
                            )
                        
                        if retry_count < max_retries:
                            next_provider = self.provider_manager.switch_provider()
                            if next_provider:
                                with self._lock:
                                    self.progress.logs.append(
                                        f"[WARNING] {code} 在 {provider_name} 下载失败，切换到 {next_provider}"
                                    )
                                time.sleep(1)
                            else:
                                with self._lock:
                                    self.progress.failed += 1
                                    self.progress.logs.append(
                                        f"[ERROR] {code} 所有数据源均下载失败: {error_msg[:100]}"
                                    )
                                break
                        else:
                            with self._lock:
                                self.progress.failed += 1
                                self.progress.logs.append(
                                    f"[ERROR] {code} 下载失败（重试{retry_count}次）: {error_msg[:100]}"
                                )
                
                time.sleep(0.1)
        
        except Exception as e:
            # 捕获未处理的异常
            with self._lock:
                self.progress.logs.append(
                    f"[ERROR] 下载线程异常: {str(e)[:100]}"
                )
        
        finally:
            with self._lock:
                self.is_running = False
                self.progress.current_code = ""
                self.progress.current_provider = ""
                
                # 添加下载完成日志
                if self.progress.completed + self.progress.failed == self.progress.total:
                    self.progress.logs.append(
                        f"[INFO] 下载任务完成：成功 {self.progress.completed} 只，失败 {self.progress.failed} 只"
                    )
    
    def stop_download(self):
        with self._lock:
            self.is_running = False


def generate_sample_data(start_date: datetime, end_date: datetime, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
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


def get_raw_data_path() -> Path:
    base_path = config_loader.get("data.storage.base_path", "./data")
    return Path(base_path) / "raw"


def get_processed_data_path() -> Path:
    base_path = config_loader.get("data.storage.base_path", "./data")
    return Path(base_path) / "processed"


def render_kline_chart(df: pd.DataFrame, title: str, show_ma: bool = True, ma_periods: list[int] | None = None, show_volume: bool = True):
    if ma_periods is None:
        ma_periods = [5, 20]

    fig = make_subplots(
        rows=2 if show_volume else 1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3] if show_volume else [1.0],
    )

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open_price"],
            high=df["high_price"],
            low=df["low_price"],
            close=df["close_price"],
            name="K线",
        ),
        row=1,
        col=1,
    )

    if show_ma and ma_periods:
        indicators = TechnicalIndicators()
        df = indicators.add_ma(df, periods=ma_periods)

        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A"]
        for i, period in enumerate(ma_periods):
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df[f"ma{period}"],
                    mode="lines",
                    name=f"MA{period}",
                    line=dict(color=colors[i % len(colors)], width=1),
                ),
                row=1,
                col=1,
            )

    if show_volume:
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="成交量",
                marker_color="rgba(76, 175, 80, 0.5)",
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        title=title,
        yaxis_title="价格",
        xaxis_rangeslider_visible=False,
        height=600,
        template="plotly_dark",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1月", step="month", stepmode="backward"),
                    dict(count=3, label="3月", step="month", stepmode="backward"),
                    dict(count=6, label="6月", step="month", stepmode="backward"),
                    dict(count=1, label="1年", step="year", stepmode="backward"),
                    dict(step="all", label="全部"),
                ])
            ),
            rangeslider=dict(visible=False),
            type="date",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


def init_session_state():
    if "download_manager" not in st.session_state:
        st.session_state.download_manager = DownloadManager()
    
    if "selected_code" not in st.session_state:
        st.session_state.selected_code = None
    
    if "page" not in st.session_state:
        st.session_state.page = "数据下载"


def render_sidebar():
    st.sidebar.title("📊 AlphaScope")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "导航",
        ["首页", "股票走势概览", "股票数据更新", "选股策略配置", "选股生成结果", "回测分析展示"],
        key="page_selector",
    )
    
    st.session_state.page = page
    
    st.sidebar.markdown("---")
    st.sidebar.info("版本: 3.0")


def render_home_page():
    """
    首页：项目介绍页面
    
    展示项目的核心功能介绍，包括：
    - 股票数据下载
    - K线查看
    - 选股超参配置
    - 候选股票排序
    - 回测结果展示
    """
    st.title("📈 AlphaScope - A股量化选股与回测平台")
    
    st.markdown("---")
    
    st.header("🎯 项目简介")
    
    st.markdown("""
    AlphaScope 是一个面向 A 股市场的 Python 原生量化研究与选股平台。
    
    本项目旨在提供：
    - **可复现**：所有策略和回测结果可复现
    - **可扩展**：支持插件化设计，易于扩展
    - **可维护**：遵循严格的开发规范，长期可维护
    - **AI 友好**：结构化设计，便于 AI 协作开发
    - **长期演进**：持续迭代，不断优化
    
    ---
    """)
    
    st.header("🚀 核心功能")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📥 数据管理")
        st.markdown("""
        - **股票数据下载**：支持多数据源自动切换
        - **增量更新**：智能识别新增数据，避免重复下载
        - **数据验真**：K线图可视化，肉眼排查数据质量
        - **本地库存**：统一管理已下载的股票数据
        """)
    
    with col2:
        st.subheader("📊 选股策略")
        st.markdown("""
        - **策略配置**：灵活的超参配置界面
        - **评分权重**：自定义评分权重配置
        - **选股结果**：展示符合选股条件的股票清单
        - **Top-N 配置**：支持配置候选股票数量
        """)
    
    with col3:
        st.subheader("📈 回测分析")
        st.markdown("""
        - **回测引擎**：支持真实数据和合成数据
        - **交易记录**：详细的交易历史记录
        - **绩效指标**：总收益率、年化收益率、最大回撤等
        - **可视化展示**：资产变化曲线、持仓变化等
        """)
    
    st.markdown("---")
    
    st.header("📋 使用指南")
    
    st.markdown("""
    1. **股票数据更新**：下载或更新股票数据
    2. **股票走势概览**：查看已下载的股票数据和K线图
    3. **选股策略配置**：配置选股策略的超参
    4. **选股生成结果**：运行选股策略，查看候选股票
    5. **回测分析展示**：对候选股票进行回测分析
    
    ---
    """)
    
    st.header("📖 技术规范")
    
    st.markdown("""
    - **数据契约**：统一的数据 Schema，保证数据质量
    - **策略隔离**：所有策略继承 BaseStrategy，完全隔离
    - **严禁未来函数**：回测系统严格禁止未来数据泄露
    - **配置优先**：所有可变运行行为必须配置化
    - **插件化设计**：核心能力支持插件扩展
    
    ---
    """)
    
    st.info("💡 提示：请从左侧导航栏选择功能模块开始使用")


def render_data_download():
    """
    股票数据更新页面
    
    提供数据下载与同步功能，支持：
    - 单股下载：下载指定股票数据
    - 批量清单：批量下载多只股票数据
    - 全量下载：下载所有A股股票数据
    
    支持增量更新策略：
    - 如果股票数据已存在，只更新新增数据
    - 如果股票数据不存在，下载全量数据
    
    支持自动数据源切换：
    - AKShare → BaoStock → Tushare
    """
    st.header("📥 股票数据更新")
    
    # 添加自动刷新机制（下载进行中时自动刷新，完成后停止）
    if st.session_state.download_manager.is_running:
        time.sleep(5)  # 每5秒刷新一次
        st.rerun()  # 自动刷新页面
    
    # ==================== 更新策略说明 ====================
    st.subheader("📋 更新策略说明")
    
    st.markdown("""
    **增量更新策略**：
    - 如果股票数据已存在，系统会自动识别最新数据日期，只下载新增数据
    - 如果股票数据不存在，系统会下载全量数据
    - 支持多数据源自动切换（AKShare → BaoStock → Tushare）
    
    **更新模式**：
    - **单股下载**：下载或更新指定股票数据
    - **批量清单**：批量下载或更新多只股票数据
    - **全量下载**：下载或更新所有A股股票数据（主板/创业板/科创板）
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚙️ 下载配置")
        
        download_mode = st.radio(
            "下载范围",
            ["单股下载", "批量清单", "全量下载"],
            horizontal=True,
        )
        
        codes = []
        
        if download_mode == "单股下载":
            code_input = st.text_input(
                "股票代码",
                placeholder="例如: 600519（只需输入6位代码）",
                help="系统会自动识别交易所并添加后缀（如：600519 → 600519.SH）",
            )
            if code_input:
                # 自动标准化股票代码
                codes = [normalize_stock_code(code_input.strip())]
            
            # 显示股票数据状态
            if codes:
                raw_path = get_raw_data_path()
                for code in codes:
                    # 从完整代码中提取纯代码（去掉交易所后缀）
                    pure_code = code.split(".")[0] if "." in code else code
                    
                    # 查找以该股票代码开头的文件
                    matching_files = list(raw_path.glob(f"{pure_code}*.parquet"))
                    
                    if matching_files:
                        # 找到匹配的文件
                        file_path = matching_files[0]
                        try:
                            df = pd.read_parquet(file_path)
                            latest_date = df["date"].max()
                            # 从文件名中提取股票名称
                            file_name = file_path.stem
                            stock_name = file_name.split(".")[-1] if len(file_name.split(".")) > 2 else ""
                            display_name = f"{code}.{stock_name}" if stock_name else code
                            st.info(f"📊 {display_name} 已有数据：{len(df)} 行，最新日期：{latest_date.strftime('%Y-%m-%d')}")
                        except Exception as e:
                            st.warning(f"⚠️ {code} 数据文件存在但读取失败：{str(e)}")
                    else:
                        st.info(f"📥 {code} 数据不存在，将下载全量数据")
        
        elif download_mode == "批量清单":
            input_method = st.radio(
                "输入方式",
                ["文本输入", "文件上传"],
                horizontal=True,
            )
            
            if input_method == "文本输入":
                codes_text = st.text_area(
                    "股票代码列表",
                    placeholder="每行一个代码，或用逗号分隔\n例如:\n600519\n000001\n300750\n\n系统会自动识别交易所",
                    height=150,
                    help="只需输入6位代码，系统会自动添加交易所后缀",
                )
                if codes_text:
                    # 自动标准化所有股票代码
                    raw_codes = [c.strip() for c in codes_text.replace("\n", ",").split(",") if c.strip()]
                    codes = [normalize_stock_code(c) for c in raw_codes]
            
            else:
                uploaded_file = st.file_uploader(
                    "上传文件",
                    type=["csv", "txt"],
                )
                if uploaded_file:
                    content = uploaded_file.read().decode("utf-8")
                    raw_codes = [c.strip() for c in content.replace("\n", ",").split(",") if c.strip()]
                    # 自动标准化所有股票代码
                    codes = [normalize_stock_code(c) for c in raw_codes]
            
            # 显示批量股票数据状态
            if codes:
                raw_path = get_raw_data_path()
                existing_count = 0
                new_count = 0
                
                for code in codes:
                    # 从完整代码中提取纯代码（去掉交易所后缀）
                    pure_code = code.split(".")[0] if "." in code else code
                    
                    # 查找以该股票代码开头的文件
                    matching_files = list(raw_path.glob(f"{pure_code}*.parquet"))
                    
                    if matching_files:
                        existing_count += 1
                    else:
                        new_count += 1
                
                st.info(f"📊 批量清单统计：共 {len(codes)} 只股票，已有数据 {existing_count} 只，新增下载 {new_count} 只")
        
        else:
            st.info("全量下载将下载所有A股股票数据（主板/创业板/科创板）")
            if st.checkbox("确认全量下载"):
                try:
                    with st.spinner("正在获取全量A股股票列表..."):
                        provider = AKShareProvider()
                        codes = provider.get_stock_list()
                    st.info(f"📊 已获取 {len(codes)} 只A股股票列表")
                except Exception as e:
                    st.error(f"获取全量股票列表失败: {str(e)}")
                    codes = []
                
                # 显示全量股票数据状态
                raw_path = get_raw_data_path()
                existing_count = 0
                new_count = 0
                
                for code in codes:
                    # 从完整代码中提取纯代码（去掉交易所后缀）
                    pure_code = code.split(".")[0] if "." in code else code
                    
                    # 查找以该股票代码开头的文件
                    matching_files = list(raw_path.glob(f"{pure_code}*.parquet"))
                    
                    if matching_files:
                        existing_count += 1
                    else:
                        new_count += 1
                
                st.info(f"📊 全量股票统计：共 {len(codes)} 只股票，已有数据 {existing_count} 只，新增下载 {new_count} 只")
        
        st.markdown("---")
        
        st.subheader("📅 时间与复权配置")
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=30),
                help="下载数据的开始日期（增量更新时自动调整）",
            )
        with col_date2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
                help="下载数据的结束日期",
            )
        
        col_adj, col_freq = st.columns(2)
        with col_adj:
            adjust_type = st.selectbox(
                "复权类型",
                ["不复权", "前复权", "后复权"],  # 默认选择不复权
            )
            adjust_map = {"前复权": "qfq", "后复权": "hfq", "不复权": "none"}
            adjust = adjust_map[adjust_type]
        
        with col_freq:
            freq = st.selectbox(
                "时间频度",
                ["日线", "周线", "5分钟线", "1分钟线"],
            )
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            start_btn = st.button(
                "🚀 开始下载",
                type="primary",
                use_container_width=True,
            )
        with col_btn2:
            stop_btn = st.button(
                "⏹️ 停止下载",
                type="secondary",
                use_container_width=True,
            )
    
    with col2:
        st.subheader("📊 下载进度")
        
        manager = st.session_state.download_manager
        
        # 使用 st.empty() 创建进度显示区域（局部刷新）
        progress_placeholder = st.empty()
        
        # 在进度区域内显示进度信息
        with progress_placeholder.container():
            if manager.progress.total > 0:
                # 进度条
                progress_bar = st.progress(manager.progress.progress_pct / 100)
                
                # 进度百分比
                st.text(f"下载进度: {manager.progress.completed}/{manager.progress.total} ({manager.progress.progress_pct:.1f}%)")
                
                # 当前下载的股票信息
                if manager.progress.current_code:
                    # 从股票代码中提取纯代码
                    pure_code = manager.progress.current_code.split(".")[0] if "." in manager.progress.current_code else manager.progress.current_code
                    
                    # 尝试从缓存中获取股票名称
                    stock_name = ""
                    try:
                        from src.data.providers.akshare_provider import AKShareProvider
                        if pure_code in AKShareProvider._stock_name_cache:
                            stock_name = AKShareProvider._stock_name_cache[pure_code]
                    except Exception:
                        pass
                    
                    if stock_name:
                        st.info(f"正在下载: {manager.progress.current_code} ({stock_name})")
                    else:
                        st.info(f"正在下载: {manager.progress.current_code}")
                
                # 下载完成后展示统计信息
                if not manager.is_running and manager.progress.completed + manager.progress.failed == manager.progress.total:
                    st.markdown("---")
                    st.subheader("📊 下载完成统计")
                    
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("总数", manager.progress.total)
                    with col_stat2:
                        st.metric("已完成", manager.progress.completed)
                    with col_stat3:
                        st.metric("失败", manager.progress.failed)
                    
                    # 展示下载失败的股票代码清单
                    if manager.progress.failed > 0:
                        st.markdown("---")
                        st.subheader("❌ 下载失败的股票")
                        
                        # 从日志中提取失败的股票代码
                        failed_codes = []
                        for log in manager.progress.logs:
                            if "[ERROR]" in log and "下载失败" in log:
                                # 提取股票代码（格式：[ERROR] 300558 下载失败...）
                                parts = log.split()
                                if len(parts) >= 2:
                                    failed_codes.append(parts[1])
                        
                        if failed_codes:
                            st.error(f"下载失败的股票代码：{', '.join(failed_codes)}")
            else:
                st.info("暂无下载任务")
        
        # 如果下载正在进行中，自动刷新页面（每2秒刷新一次）
        if manager.is_running:
            time.sleep(2)
            st.rerun()
    
    if start_btn and codes:
        manager.start_download(
            codes=codes,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.min.time()),
            adjust=adjust,
        )
        st.rerun()  # 立即刷新页面，显示下载进度
    
    if stop_btn:
        manager.stop_download()
        st.warning("已停止下载")
        st.rerun()  # 立即刷新页面，更新状态


def render_stock_overview():
    """
    股票走势概览页面
    
    合并了原有的"本地库存"和"K线验真"页面，分为三部分：
    1. 上部分：展示整体数据情况
    2. 中间部分：展示特定股票的数据明细
    3. 下部分：展示该股票的历史K线图
    """
    st.header("📊 股票走势概览")
    
    # 检查原始数据目录
    raw_path = get_raw_data_path()
    processed_path = get_processed_data_path()
    
    if not raw_path.exists():
        st.warning("原始数据目录不存在，请先在'股票数据更新'页面下载数据")
        return
    
    # 获取原始数据文件
    raw_files = list(raw_path.glob("*.parquet"))
    
    if not raw_files:
        st.info("暂无已下载的股票数据，请先在'股票数据更新'页面下载数据")
        return
    
    # ==================== 上部分：整体数据情况 ====================
    st.subheader("📈 整体数据概览")
    
    # 导入 AKShareProvider 以访问股票名称缓存
    from src.data.providers.akshare_provider import AKShareProvider
    
    # 确保股票名称缓存已加载
    if not AKShareProvider._cache_loaded:
        try:
            import akshare as ak
            df_stocks = ak.stock_info_a_code_name()
            for _, row in df_stocks.iterrows():
                code = row.get("code", "")
                name = row.get("name", "")
                if code and name:
                    AKShareProvider._stock_name_cache[code] = name
            AKShareProvider._cache_loaded = True
        except Exception as e:
            st.warning(f"加载股票名称缓存失败: {str(e)}")
    
    data_info = []
    for file in raw_files:
        try:
            df = pd.read_parquet(file)
            
            # 获取股票名称（从 parquet 文件中读取）
            stock_name = ""
            if "name" in df.columns and not df.empty:
                stock_name = df.iloc[0]["name"]
            
            # 如果 parquet 文件中没有股票名称，从缓存中获取
            if not stock_name:
                # 从文件名中提取股票代码（去掉交易所后缀）
                file_stem = file.stem
                pure_code = file_stem.split(".")[0] if "." in file_stem else file_stem
                
                # 从缓存中获取股票名称
                if pure_code in AKShareProvider._stock_name_cache:
                    stock_name = AKShareProvider._stock_name_cache[pure_code]
            
            data_info.append({
                "股票代码": file.stem,
                "股票名称": stock_name,
                "数据行数": len(df),
                "开始日期": df["date"].min() if "date" in df.columns else "N/A",
                "结束日期": df["date"].max() if "date" in df.columns else "N/A",
                "文件大小": f"{file.stat().st_size / 1024:.2f} KB",
            })
        except Exception as e:
            st.error(f"读取文件 {file.name} 失败: {str(e)}")
    
    if data_info:
        # 展示统计指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总股票数", len(data_info))
        with col2:
            st.metric("总数据行数", sum([d["数据行数"] for d in data_info]))
        with col3:
            total_size = sum([file.stat().st_size for file in raw_files]) / (1024 * 1024)
            st.metric("总文件大小", f"{total_size:.2f} MB")
        with col4:
            # 计算平均数据行数
            avg_rows = sum([d["数据行数"] for d in data_info]) / len(data_info)
            st.metric("平均数据行数", f"{avg_rows:.0f}")
        
        st.markdown("---")
        
        # 展示股票列表（包含股票名称）
        df_info = pd.DataFrame(data_info)
        st.dataframe(df_info, use_container_width=True)
        
        # 检查预处理数据
        if processed_path.exists():
            processed_files = list(processed_path.glob("*.parquet"))
            if processed_files:
                st.markdown("---")
                st.info(f"📊 预处理数据：共 {len(processed_files)} 只股票，存储在 {processed_path}")
    
    st.markdown("---")
    
    # ==================== 中间部分：特定股票数据明细 ====================
    st.subheader("📋 股票数据明细")
    
    # 股票选择下拉框
    selected_stock = st.selectbox(
        "选择股票代码",
        [file.stem for file in raw_files],
        help="选择要查看的股票代码",
    )
    
    if selected_stock:
        file_path = raw_path / f"{selected_stock}.parquet"
        
        try:
            df = pd.read_parquet(file_path)
            
            if df.empty:
                st.warning("该股票数据为空")
                return
            
            # 确保日期列是 datetime 类型
            df["date"] = pd.to_datetime(df["date"])
            
            # 添加涨跌幅列（如果不存在）
            if "pct_chg" not in df.columns:
                df["pct_chg"] = ((df["close_price"] - df["close_price"].shift(1)) / df["close_price"].shift(1) * 100).round(2)
            
            # 添加换手率列（如果不存在）
            if "turn" not in df.columns:
                # 换手率 = 成交量 / 流通股本，这里用简化计算
                df["turn"] = (df["volume"] / df["volume"].mean() * 100).round(2)
            
            # 展示股票数据表格（按日期倒序排序）
            display_df = df[["date", "open_price", "high_price", "low_price", "close_price", "volume", "amount", "pct_chg", "turn"]].copy()
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
            display_df.columns = ["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量", "成交额", "涨跌幅%", "换手率%"]
            
            # 按日期倒序排序（优先展示最近交易日数据）
            display_df = display_df.sort_values("日期", ascending=False)
            
            st.dataframe(display_df, use_container_width=True)
            
            # 展示数据统计
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("数据行数", len(df))
            with col2:
                st.metric("开始日期", df["date"].min().strftime("%Y-%m-%d"))
            with col3:
                st.metric("结束日期", df["date"].max().strftime("%Y-%m-%d"))
            with col4:
                latest_close = df.iloc[-1]["close_price"]
                st.metric("最新收盘价", f"{latest_close:.2f}")
            
        except Exception as e:
            st.error(f"读取数据失败: {str(e)}")
            return
    
    st.markdown("---")
    
    # ==================== 下部分：K线图可视化 ====================
    st.subheader("📈 K线图可视化")
    
    if selected_stock:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("**⚙️ 图表配置**")
            
            show_ma = st.checkbox("显示均线", value=True)
            ma_periods = [5, 20]
            if show_ma:
                ma_periods = st.multiselect(
                    "均线周期",
                    [5, 10, 20, 60],
                    default=[5, 20],
                )
            
            show_volume = st.checkbox("显示成交量", value=True)
        
        with col2:
            file_path = raw_path / f"{selected_stock}.parquet"
            
            try:
                df = pd.read_parquet(file_path)
                
                if df.empty:
                    st.warning("该股票数据为空")
                    return
                
                df["date"] = pd.to_datetime(df["date"])
                
                stock_name = ""
                if "name" in df.columns and not df.empty:
                    stock_name = df.iloc[0]["name"]
                
                title_text = f"{selected_stock} K线图"
                if stock_name:
                    title_text = f"{selected_stock}.{stock_name} K线图"
                
                render_kline_chart(df, title_text, show_ma=show_ma, ma_periods=ma_periods, show_volume=show_volume)
                
            except Exception as e:
                st.error(f"绘制K线图失败: {str(e)}")


def render_strategy_config():
    """
    选股策略配置页面
    
    提供选股策略的超参配置，包括：
    - 任务配置（定时任务启停时间、日志级别等）
    - 数据抓取配置（数据源优先级、最大重试次数等）
    - 选股策略超参（市值区间、股价区间、涨跌停配置等）
    - 评分权重配置（价格、涨停、市值等权重）
    
    所有配置与 ./config/settings.yaml 文件同步
    """
    st.header("⚙️ 选股策略配置")
    
    # ==================== 导入配置类 ====================
    from src.strategy.selection_strategy import SelectionConfig
    
    # ==================== 从配置文件读取参数 ====================
    selection_config = SelectionConfig.from_config()
    
    # 加载配置
    config = config_loader
    
    # ==================== 任务配置 ====================
    st.subheader("📋 任务配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**定时任务配置**")
        
        # 定时任务启停时间
        task_start_time = st.time_input(
            "任务启动时间",
            value=datetime.strptime("09:30", "%H:%M").time(),
            help="每日定时任务启动时间",
        )
        
        task_end_time = st.time_input(
            "任务停止时间",
            value=datetime.strptime("15:00", "%H:%M").time(),
            help="每日定时任务停止时间",
        )
        
        # 日志级别（从配置文件读取）
        log_level_default = config.get("logging.level", "INFO")
        log_level_index = ["DEBUG", "INFO", "WARNING", "ERROR"].index(log_level_default) if log_level_default in ["DEBUG", "INFO", "WARNING", "ERROR"] else 1
        
        log_level = st.selectbox(
            "日志级别",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            index=log_level_index,
            help="系统日志记录级别",
        )
    
    with col2:
        st.markdown("**任务说明**")
        
        # 任务说明（替代任务状态子模块）
        st.info("""
        **任务说明**：
        - 页面打开即表示任务已启动
        - 定时任务会在指定时间自动运行
        - 无需手动启动或停止任务
        """)
    
    st.markdown("---")
    
    # ==================== 数据抓取配置 ====================
    st.subheader("📥 数据抓取配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**数据源配置**")
        
        # 数据源优先级（从配置文件读取）
        data_sources_default = ["akshare", "baostock", "tushare"]
        data_sources = st.multiselect(
            "数据源优先级",
            ["akshare", "baostock", "tushare"],
            default=data_sources_default,
            help="数据源优先级顺序，系统会按顺序尝试下载",
        )
        
        # 最大重试次数（从配置文件读取）
        max_retry_times_default = config.get("data.providers.akshare.retry_times", 3)
        max_retry_times = st.slider(
            "最大重试次数",
            min_value=1,
            max_value=10,
            value=max_retry_times_default,
            help="数据下载失败时的最大重试次数",
        )
        
        # 重试延迟（秒）（从配置文件读取）
        retry_delay_default = config.get("data.providers.akshare.retry_delay", 1.0)
        retry_delay = st.slider(
            "重试延迟（秒）",
            min_value=0.5,
            max_value=5.0,
            value=retry_delay_default,
            step=0.5,
            help="每次重试之间的延迟时间",
        )
    
    with col2:
        st.markdown("**数据管理配置**")
        
        # 数据滑窗保留天数（从配置文件读取）
        data_retention_days_default = config.get("data.update.lookback_days", 30)
        data_retention_days = st.slider(
            "数据滑窗保留天数",
            min_value=30,
            max_value=365,
            value=data_retention_days_default,
            help="保留最近N天的数据，超过此天数的数据将被清理",
        )
        
        # 并行工作线程数
        parallel_workers = st.slider(
            "并行工作线程数",
            min_value=1,
            max_value=10,
            value=3,
            help="并行下载数据的线程数量",
        )
        
        # 增量更新开关（从配置文件读取）
        incremental_update_default = config.get("data.update.incremental", True)
        incremental_update = st.checkbox(
            "启用增量更新",
            value=incremental_update_default,
            help="只更新新增数据，避免重复下载",
        )
    
    st.markdown("---")
    
    # ==================== 选股策略超参 ====================
    st.subheader("📊 选股策略超参")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**市值与价格区间**")
        
        # 总市值区间（亿元）（从配置文件读取）
        market_cap_min = st.number_input(
            "最小市值（亿元）",
            min_value=0,
            max_value=20000,
            value=int(selection_config.market_cap_min),
            help="筛选市值大于此值的股票",
        )
        
        market_cap_max = st.number_input(
            "最大市值（亿元）",
            min_value=0,
            max_value=20000,
            value=int(selection_config.market_cap_max),
            help="筛选市值小于此值的股票",
        )
        
        # 股价区间（元）（从配置文件读取）
        price_min = st.number_input(
            "最小股价（元）",
            min_value=0.0,
            max_value=2000.0,
            value=selection_config.price_min,
            step=0.5,
            help="筛选股价大于此值的股票",
        )
        
        price_max = st.number_input(
            "最大股价（元）",
            min_value=0.0,
            max_value=2000.0,
            value=selection_config.price_max,
            step=0.5,
            help="筛选股价小于此值的股票",
        )
    
    with col2:
        st.markdown("**涨跌停配置**")
        
        # 涨跌停数量区间（从配置文件读取）
        limit_up_min = st.number_input(
            "最小涨停次数",
            min_value=0,
            max_value=20,
            value=selection_config.limit_up_min,
            help="筛选涨停次数大于此值的股票",
        )
        
        limit_down_max = st.number_input(
            "最大跌停次数",
            min_value=0,
            max_value=20,
            value=selection_config.limit_down_max,
            help="筛选跌停次数小于此值的股票",
        )
        
        # 涨跌停统计周期（天）（从配置文件读取）
        limit_stat_period = st.slider(
            "涨跌停统计周期（天）",
            min_value=5,
            max_value=60,
            value=selection_config.limit_stat_period,
            help="统计最近N天的涨跌停次数",
        )
        
        # 最大涨幅阈值（从配置文件读取）
        max_up_threshold = st.slider(
            "最大涨幅阈值（%）",
            min_value=0.0,
            max_value=20.0,
            value=selection_config.max_up_threshold,
            step=0.5,
            help="用于判断涨停的涨幅阈值",
        )
        
        # 最大跌幅阈值（从配置文件读取）
        max_down_threshold = st.slider(
            "最大跌幅阈值（%）",
            min_value=-20.0,
            max_value=0.0,
            value=selection_config.max_down_threshold,
            step=0.5,
            help="用于判断跌停的跌幅阈值",
        )
    
    with col3:
        st.markdown("**持仓配置**")
        
        # 初始资金量（从配置文件读取）
        initial_cash = st.number_input(
            "初始资金量（元）",
            min_value=10000,
            max_value=100000000,
            value=int(selection_config.initial_cash),
            step=10000,
            help="回测初始资金量",
        )
        
        # 最大持仓股票数量（从配置文件读取）
        max_positions = st.slider(
            "最大持仓股票数量",
            min_value=1,
            max_value=20,
            value=selection_config.max_positions,
            help="同时持有的最大股票数量",
        )
        
        # Top-N 配置（从配置文件读取）
        top_n = st.slider(
            "候选股票数量（Top-N）",
            min_value=5,
            max_value=20,
            value=selection_config.top_n,
            help="选股策略输出的候选股票数量",
        )
        
        # 最小评分阈值（从配置文件读取）
        min_score_threshold = st.slider(
            "最小评分阈值",
            min_value=0.0,
            max_value=100.0,
            value=selection_config.min_score_threshold,
            step=5.0,
            help="筛选评分大于此值的股票",
        )
    
    st.markdown("---")
    
    # ==================== 评分权重配置 ====================
    st.subheader("⚖️ 评分权重配置")
    
    st.markdown("**调整均线策略的评分权重（基于实际选股因子）**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**均线排列权重**")
        
        # 均线排列权重（从配置文件读取）
        ma_alignment_weight = st.slider(
            "均线排列权重 (%)",
            min_value=0,
            max_value=100,
            value=int(selection_config.ma_alignment_weight),
            help="均线排列（MA5 > MA10 > MA20）的评分权重",
        )
        
        st.info("均线排列：多头排列（强势上涨）得分最高")
    
    with col2:
        st.markdown("**价格位置权重**")
        
        # 价格位置权重（从配置文件读取）
        price_position_weight = st.slider(
            "价格位置权重 (%)",
            min_value=0,
            max_value=100,
            value=int(selection_config.price_position_weight),
            help="价格相对于均线的位置权重",
        )
        
        st.info("价格位置：价格在均线之上的得分较高")
    
    with col3:
        st.markdown("**趋势强度权重**")
        
        # 趋势强度权重（从配置文件读取）
        trend_strength_weight = st.slider(
            "趋势强度权重 (%)",
            min_value=0,
            max_value=100,
            value=int(selection_config.trend_strength_weight),
            help="趋势强度的评分权重",
        )
        
        st.info("趋势强度：均线斜率和发散程度的权重")
    
    # 显示权重总和
    total_weight = ma_alignment_weight + price_position_weight + trend_strength_weight
    
    if total_weight == 100:
        st.success(f"权重总和：{total_weight}% ✓")
    else:
        st.warning(f"权重总和：{total_weight}%（建议调整为100%）")
    
    st.markdown("---")
    
    # ==================== 保存配置 ====================
    st.subheader("💾 配置管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        save_config_btn = st.button(
            "💾 保存配置",
            type="primary",
            use_container_width=True,
        )
    
    with col2:
        reset_config_btn = st.button(
            "🔄 重置配置",
            type="secondary",
            use_container_width=True,
        )
    
    # 处理按钮事件
    if save_config_btn:
        # 保存选股策略配置到配置文件
        config.update("strategy.selection.market_cap_min", market_cap_min)
        config.update("strategy.selection.market_cap_max", market_cap_max)
        config.update("strategy.selection.price_min", price_min)
        config.update("strategy.selection.price_max", price_max)
        config.update("strategy.selection.limit_up_min", limit_up_min)
        config.update("strategy.selection.limit_down_max", limit_down_max)
        config.update("strategy.selection.limit_stat_period", limit_stat_period)
        config.update("strategy.selection.max_up_threshold", max_up_threshold)
        config.update("strategy.selection.max_down_threshold", max_down_threshold)
        config.update("strategy.selection.initial_cash", initial_cash)
        config.update("strategy.selection.max_positions", max_positions)
        config.update("strategy.selection.top_n", top_n)
        config.update("strategy.selection.min_score_threshold", min_score_threshold)
        config.update("strategy.selection.ma_alignment_weight", ma_alignment_weight)
        config.update("strategy.selection.price_position_weight", price_position_weight)
        config.update("strategy.selection.trend_strength_weight", trend_strength_weight)
        
        # 保存数据抓取配置到配置文件
        config.update("data.providers.akshare.retry_times", max_retry_times)
        config.update("data.providers.akshare.retry_delay", retry_delay)
        config.update("data.update.lookback_days", data_retention_days)
        config.update("data.update.incremental", incremental_update)
        
        # 保存日志级别到配置文件
        config.update("logging.level", log_level)
        
        st.success("配置已保存到 ./config/settings.yaml")
    
    if reset_config_btn:
        # 重置配置为默认值
        default_config = SelectionConfig()
        config.update("strategy.selection.market_cap_min", default_config.market_cap_min)
        config.update("strategy.selection.market_cap_max", default_config.market_cap_max)
        config.update("strategy.selection.price_min", default_config.price_min)
        config.update("strategy.selection.price_max", default_config.price_max)
        config.update("strategy.selection.limit_up_min", default_config.limit_up_min)
        config.update("strategy.selection.limit_down_max", default_config.limit_down_max)
        config.update("strategy.selection.limit_stat_period", default_config.limit_stat_period)
        config.update("strategy.selection.max_up_threshold", default_config.max_up_threshold)
        config.update("strategy.selection.max_down_threshold", default_config.max_down_threshold)
        config.update("strategy.selection.initial_cash", default_config.initial_cash)
        config.update("strategy.selection.max_positions", default_config.max_positions)
        config.update("strategy.selection.top_n", default_config.top_n)
        config.update("strategy.selection.min_score_threshold", default_config.min_score_threshold)
        config.update("strategy.selection.ma_alignment_weight", default_config.ma_alignment_weight)
        config.update("strategy.selection.price_position_weight", default_config.price_position_weight)
        config.update("strategy.selection.trend_strength_weight", default_config.trend_strength_weight)
        
        st.warning("配置已重置为默认值")


def render_stock_selection_result():
    """
    选股生成结果页面
    
    展示符合选股条件的股票清单，包括：
    - 显示选股策略配置的超参
    - 运行选股策略按钮
    - 展示候选股票清单（按评分倒排排序）
    - 展示股票代码、得分、可交易区间等
    
    基于本地已下载的股票数据进行选股
    """
    st.header("🎯 选股生成结果")
    
    # ==================== 导入选股策略类 ====================
    from src.strategy.selection_strategy import SelectionConfig, SelectionStrategy
    
    # ==================== 选股策略配置概览 ====================
    st.subheader("📋 当前选股策略配置")
    
    # 从配置文件读取选股策略配置
    selection_config = SelectionConfig.from_config()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("初始资金量", f"{selection_config.initial_cash:,} 元")
        st.metric("最大持仓数", f"{selection_config.max_positions} 只")
    
    with col2:
        st.metric("候选股票数（Top-N）", f"{selection_config.top_n} 只")
        st.metric("最小评分阈值", f"{selection_config.min_score_threshold}")
    
    with col3:
        st.metric("市值区间", f"{selection_config.market_cap_min}-{selection_config.market_cap_max} 亿元")
        st.metric("股价区间", f"{selection_config.price_min}-{selection_config.price_max} 元")
    
    with col4:
        st.metric("涨跌停统计周期", f"{selection_config.limit_stat_period} 天")
        st.metric("最大涨幅阈值", f"{selection_config.max_up_threshold}%")
    
    st.markdown("---")
    
    # ==================== 检查本地数据 ====================
    st.subheader("📊 本地数据检查")
    
    raw_path = get_raw_data_path()
    
    if not raw_path.exists():
        st.warning("原始数据目录不存在，请先在'股票数据更新'页面下载数据")
        return
    
    raw_files = list(raw_path.glob("*.parquet"))
    
    if not raw_files:
        st.warning("暂无已下载的股票数据，请先在'股票数据更新'页面下载数据")
        return
    
    st.info(f"已发现 {len(raw_files)} 只股票数据，可用于选股分析")
    
    st.markdown("---")
    
    # ==================== 运行选股策略 ====================
    st.subheader("🚀 运行选股策略")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info("点击下方按钮，基于本地已下载的股票数据，运行选股策略")
    
    with col2:
        run_selection_btn = st.button(
            "🚀 运行选股策略",
            type="primary",
            use_container_width=True,
        )
    
    st.markdown("---")
    
    # ==================== 选股结果展示 ====================
    st.subheader("📊 候选股票清单")
    
    if run_selection_btn:
        st.info("正在运行选股策略...")
        
        # 创建选股策略实例
        strategy = SelectionStrategy(selection_config)
        
        # 基于本地数据进行选股
        selection_results = []
        
        for file in raw_files:
            try:
                df = pd.read_parquet(file)
                
                if df.empty:
                    continue
                
                # 确保日期列是 datetime 类型
                df["date"] = pd.to_datetime(df["date"])
                
                # 获取股票名称
                stock_name = ""
                if "name" in df.columns and not df.empty:
                    stock_name = df.iloc[0]["name"]
                
                # 如果 parquet 文件中没有股票名称，从缓存中获取
                if not stock_name:
                    # 从文件名中提取股票代码（去掉交易所后缀）
                    file_stem = file.stem
                    pure_code = file_stem.split(".")[0] if "." in file_stem else file_stem
                    
                    # 从缓存中获取股票名称
                    if pure_code in AKShareProvider._stock_name_cache:
                        stock_name = AKShareProvider._stock_name_cache[pure_code]
                
                # 准备数据（计算技术指标）
                df = strategy.prepare(df)
                
                # 只保留最近limit_stat_period天的数据（用于评分）
                df_recent = df.tail(selection_config.limit_stat_period)
                
                # 获取最新数据
                latest = df.iloc[-1]
                
                # 筛选股票（根据配置的超参）
                if not strategy.filter_stock(latest, df):
                    continue
                
                # 计算评分（使用新的选股策略，只传入最近limit_stat_period天的数据）
                score = strategy.score_stock(file.stem, df_recent)
                
                # 获取最新收盘价和涨跌幅
                latest_close = latest.get("close_price", 0)
                latest_pct_chg = latest.get("pct_chg", 0)
                
                # 确保涨跌幅是数值类型
                try:
                    latest_pct_chg = float(latest_pct_chg) if latest_pct_chg else 0.0
                except (ValueError, TypeError):
                    latest_pct_chg = 0.0
                
                # 判断是否可交易（简单判断：涨跌幅在 -10% 到 10% 之间）
                tradable = "是" if -10 <= latest_pct_chg <= 10 else "否"
                
                selection_results.append({
                    "股票代码": file.stem,
                    "股票名称": stock_name,
                    "评分": score,
                    "股价（元）": latest_close,
                    "涨跌幅": f"{latest_pct_chg:.2f}%",
                    "可交易": tradable,
                })
                
            except Exception as e:
                st.warning(f"处理股票 {file.stem} 时出错: {str(e)}")
                continue
        
        # 按评分倒排排序
        selection_results = sorted(selection_results, key=lambda x: x["评分"], reverse=True)
        
        # 只展示 Top-N（从配置读取）
        selection_results = selection_results[:selection_config.top_n]
        
        if selection_results:
            df_results = pd.DataFrame(selection_results)
            st.dataframe(df_results, use_container_width=True)
            
            # 统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("候选股票数", len(selection_results))
            with col2:
                avg_score = sum([r["评分"] for r in selection_results]) / len(selection_results)
                st.metric("平均评分", f"{avg_score:.2f}")
            with col3:
                tradable_count = sum([1 for r in selection_results if r["可交易"] == "是"])
                st.metric("可交易股票数", tradable_count)
            
            st.success("选股策略执行完成！")
            
            # 保存选股结果到 session_state（供回测使用）
            st.session_state.selection_results = selection_results
        else:
            st.warning("没有找到符合条件的股票")
    else:
        st.info("请点击'运行选股策略'按钮生成候选股票清单")


def render_backtest_display():
    """
    回测分析展示页面
    
    展示回测结果，包括：
    - 回测超参配置
    - 运行回测按钮
    - 回测进度展示
    - 回测结果概览（总收益率、年化收益率、最大回撤等）
    - 资产变化曲线
    - 持仓变化展示
    - 交易记录明细
    
    直接从本地数据中读取全量股票数据进行回测
    """
    st.header("📈 回测分析展示")
    
    # 定义数据路径
    raw_path = get_raw_data_path()
    
    # ==================== 检查本地数据 ====================
    st.subheader("📊 本地数据检查")
    
    # 检查本地数据目录是否存在
    if not raw_path.exists():
        st.warning("原始数据目录不存在，请先在'股票数据更新'页面下载数据")
        return
    
    # 获取本地数据文件
    raw_files = list(raw_path.glob("*.parquet"))
    
    if not raw_files:
        st.warning("暂无已下载的股票数据，请先在'股票数据更新'页面下载数据")
        return
    
    st.info(f"已发现 {len(raw_files)} 只股票数据，可用于回测分析")
    
    st.markdown("---")
    
    # ==================== 回测超参配置 ====================
    st.subheader("⚙️ 回测配置")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**时间配置**")
        
        backtest_start_date = st.date_input(
            "回测开始日期",
            value=datetime(2024, 1, 1),
            help="回测开始日期",
        )
        
        backtest_end_date = st.date_input(
            "回测结束日期",
            value=datetime(2024, 3, 31),
            help="回测结束日期",
        )
    
    with col2:
        st.markdown("**资金配置**")
        
        initial_cash = st.number_input(
            "初始资金（元）",
            min_value=10000,
            max_value=100000000,
            value=1000000,
            step=10000,
            help="回测初始资金",
        )
        
        max_positions = st.slider(
            "最大持仓数",
            min_value=1,
            max_value=50,
            value=10,
            help="最大持仓股票数量",
        )
    
    with col3:
        st.markdown("**风控配置**")
        
        max_drawdown = st.slider(
            "最大回撤限制 (%)",
            min_value=5,
            max_value=50,
            value=20,
            help="最大回撤限制",
        )
        
        stop_loss = st.slider(
            "止损线 (%)",
            min_value=-20,
            max_value=-1,
            value=-8,
            help="止损线",
        )
    
    st.markdown("---")
    
    # ==================== 运行回测 ====================
    st.subheader("🚀 运行回测")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info("点击下方按钮，基于选股生成的股票池进行回测分析")
    
    with col2:
        run_backtest_btn = st.button(
            "🚀 运行回测",
            type="primary",
            use_container_width=True,
        )
    
    st.markdown("---")
    
    # ==================== 回测执行 ====================
    if run_backtest_btn:
        st.subheader("📊 回测执行")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            from src.backtest.backtest_engine import BacktestEngine
            from src.strategy.selection_strategy import SelectionStrategy, SelectionConfig
            
            selection_config = SelectionConfig.from_config()
            strategy = SelectionStrategy(selection_config)
            
            all_data = []
            total_files = len(raw_files)
            for idx, file_path in enumerate(raw_files):
                try:
                    df = pd.read_parquet(file_path)
                    if not df.empty:
                        df["date"] = pd.to_datetime(df["date"])
                        df = df[(df["date"] >= pd.Timestamp(backtest_start_date)) & 
                                (df["date"] <= pd.Timestamp(backtest_end_date))]
                        if not df.empty:
                            all_data.append(df)
                except Exception as e:
                    st.warning(f"读取文件 {file_path.name} 时出错: {str(e)}")
                    continue
                
                pct = int((idx + 1) / total_files * 50) if total_files > 0 else 50
                progress_bar.progress(pct)
                status_text.text(f"加载数据: {idx + 1}/{total_files} ({pct}%)")
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                
                engine = BacktestEngine(
                    strategy=strategy,
                    initial_cash=initial_cash,
                )
                
                def on_progress(current, total):
                    pct = 50 + int(current / total * 50) if total > 0 else 100
                    progress_bar.progress(pct)
                    status_text.text(f"回测进度: {current}/{total} ({pct - 50}%)")
                
                result = engine.run(combined_df, progress_callback=on_progress)
                
                progress_bar.progress(100)
                status_text.text("回测完成！")
                st.success("回测分析完成！")
                
                st.markdown("---")
                
                # ==================== 回测结果概览 ====================
                st.subheader("📊 回测结果概览")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("总收益率", f"{result.total_return:.2f}%")
                
                with col2:
                    st.metric("年化收益率", f"{result.annual_return:.2f}%")
                
                with col3:
                    st.metric("最大回撤", f"{result.max_drawdown:.2f}%")
                
                with col4:
                    st.metric("总交易次数", result.total_trades)
                
                with col5:
                    st.metric("成交胜率", f"{result.win_rate:.2f}%")
                
                st.markdown("---")
                
                # ==================== 资产变化曲线 ====================
                st.subheader("📈 资产变化曲线")
                
                if result.portfolio_states:
                    dates = [state.date for state in result.portfolio_states]
                    asset_values = [state.total_value for state in result.portfolio_states]
                    
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=dates,
                            y=asset_values,
                            mode="lines",
                            name="总资产",
                            line=dict(color="#4ECDC4", width=2),
                        )
                    )
                    
                    fig.update_layout(
                        title="总资产变化曲线",
                        xaxis_title="日期",
                        yaxis_title="总资产（元）",
                        template="plotly_dark",
                        height=400,
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("回测期间没有资产变化数据")
                
                st.markdown("---")
                
                # ==================== 交易记录明细 ====================
                st.subheader("📋 交易记录明细")
                
                if result.transactions:
                    trade_records = []
                    for trans in result.transactions:
                        trade_records.append({
                            "交易时间": trans.date.strftime("%Y-%m-%d"),
                            "股票代码": trans.code,
                            "操作": "买入" if trans.action == "BUY" else "卖出",
                            "股价": trans.price,
                            "数量": trans.shares,
                            "金额": trans.amount,
                            "手续费": trans.commission,
                            "盈利": trans.profit,
                            "账户总金额": trans.total_value,
                            "原因": trans.reason,
                        })
                    
                    df_trades = pd.DataFrame(trade_records)
                    st.dataframe(df_trades, use_container_width=True)
                    st.info(f"共 {len(trade_records)} 条交易记录")
                else:
                    st.info("回测期间没有产生交易记录")
            else:
                status_text.text("没有找到符合回测时间范围的数据")
                st.warning("没有找到符合回测时间范围的数据")
        
        except Exception as e:
            status_text.text(f"回测执行失败: {str(e)}")
            st.error(f"回测执行失败: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
    else:
        st.info("请点击'运行回测'按钮开始回测分析")


def main():
    init_session_state()
    
    render_sidebar()
    
    page = st.session_state.page
    
    if page == "首页":
        render_home_page()
    elif page == "股票走势概览":
        render_stock_overview()
    elif page == "股票数据更新":
        render_data_download()
    elif page == "选股策略配置":
        render_strategy_config()
    elif page == "选股生成结果":
        render_stock_selection_result()
    elif page == "回测分析展示":
        render_backtest_display()


if __name__ == "__main__":
    main()
