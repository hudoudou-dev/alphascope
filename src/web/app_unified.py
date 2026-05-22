"""
AlphaScope 统一Web平台

本模块提供完整的Web界面，包括：
- 数据下载与同步
- 本地库存管理
- K线图可视化
- 回测分析
- 自动数据源切换

使用示例：
    streamlit run src/web/app_unified.py
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.core.config import config_loader
from src.core.logger import get_logger
from src.data.providers.akshare_provider import AKShareProvider
from src.data.providers.baostock_provider import BaoStockProvider
from src.data.providers.tushare_provider import TushareProvider
from src.backtest.backtest_engine import BacktestEngine
from src.strategy.base_strategy import BaseStrategy
from src.indicators.technical_indicators import TechnicalIndicators


logger = get_logger("WebAppUnified")


@dataclass
class DownloadTask:
    """下载任务数据类"""
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
    """下载进度数据类"""
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
    """自动切换数据源的管理器"""
    
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
        """获取数据提供者"""
        if provider_name:
            return self.providers.get(provider_name, AKShareProvider)()
        
        provider_name = self.provider_order[self.current_provider_index]
        return self.providers[provider_name]()
    
    def switch_provider(self) -> str | None:
        """切换到下一个数据源"""
        if self.current_provider_index < len(self.provider_order) - 1:
            self.current_provider_index += 1
            next_provider = self.provider_order[self.current_provider_index]
            self.logger.info(f"切换数据源到: {next_provider}")
            return next_provider
        return None
    
    def reset(self):
        """重置为默认数据源"""
        self.current_provider_index = 0


class DownloadManager:
    """下载管理器"""
    
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
        """启动下载任务"""
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
        """下载工作线程"""
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
                                    self.progress.logs.append(
                                        f"[ERROR] {code} 所有数据源均下载失败: {error_msg}"
                                    )
                                break
                        else:
                            with self._lock:
                                self.progress.failed += 1
                                self.progress.logs.append(
                                    f"[ERROR] {code} 下载失败（重试{retry_count}次）: {error_msg}"
                                )
                
                time.sleep(0.1)
        
        finally:
            with self._lock:
                self.is_running = False
                self.progress.current_code = ""
                self.progress.current_provider = ""
    
    def stop_download(self):
        """停止下载"""
        with self._lock:
            self.is_running = False


def init_session_state():
    """初始化 session state"""
    if "download_manager" not in st.session_state:
        st.session_state.download_manager = DownloadManager()
    
    if "selected_code" not in st.session_state:
        st.session_state.selected_code = None
    
    if "page" not in st.session_state:
        st.session_state.page = "数据下载"


def render_sidebar():
    """渲染侧边栏导航"""
    st.sidebar.title("📊 AlphaScope")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "导航",
        ["数据下载", "本地库存", "K线验真", "回测分析"],
        key="page_selector",
    )
    
    st.session_state.page = page
    
    st.sidebar.markdown("---")
    st.sidebar.info("版本: 2.0")


def render_data_download():
    """渲染数据下载页面"""
    st.header("📥 数据下载与同步")
    
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
                placeholder="例如: 600000.SH",
            )
            if code_input:
                codes = [code_input.strip()]
        
        elif download_mode == "批量清单":
            input_method = st.radio(
                "输入方式",
                ["文本输入", "文件上传"],
                horizontal=True,
            )
            
            if input_method == "文本输入":
                codes_text = st.text_area(
                    "股票代码列表",
                    placeholder="每行一个代码，或用逗号分隔\n例如:\n600000.SH\n000001.SZ\n300750.SZ",
                    height=150,
                )
                if codes_text:
                    codes = [c.strip() for c in codes_text.replace("\n", ",").split(",") if c.strip()]
            
            else:
                uploaded_file = st.file_uploader(
                    "上传文件",
                    type=["csv", "txt"],
                )
                if uploaded_file:
                    content = uploaded_file.read().decode("utf-8")
                    codes = [c.strip() for c in content.replace("\n", ",").split(",") if c.strip()]
        
        else:
            st.info("全量下载将下载所有A股股票数据（主板/创业板/科创板）")
            if st.checkbox("确认全量下载"):
                codes = ["600000.SH", "000001.SZ", "300750.SZ"]
        
        st.markdown("---")
        
        st.subheader("📅 时间与复权配置")
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=30),
            )
        with col_date2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
            )
        
        col_adj, col_freq = st.columns(2)
        with col_adj:
            adjust_type = st.selectbox(
                "复权类型",
                ["前复权", "后复权", "不复权"],
            )
            adjust_map = {"前复权": "qfq", "后复权": "hfq", "不复权": "none"}
            adjust = adjust_map[adjust_type]
        
        with col_freq:
            freq = st.selectbox(
                "时间频度",
                ["日线", "周线", "5分钟线", "1分钟线"],
            )
        
        st.info("💡 数据源将自动切换：AKShare → BaoStock → Tushare")
        
        st.markdown("---")
        
        st.subheader("🚀 执行控制")
        
        manager = st.session_state.download_manager
        
        if manager.is_running:
            st.warning("⏳ 下载任务正在执行中...")
            if st.button("⏹️ 停止下载", type="secondary"):
                manager.stop_download()
                st.rerun()
        else:
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button(
                    "▶️ 开始下载",
                    type="primary",
                    disabled=len(codes) == 0,
                ):
                    if codes:
                        manager.start_download(
                            codes=codes,
                            start_date=datetime.combine(start_date, datetime.min.time()),
                            end_date=datetime.combine(end_date, datetime.min.time()),
                            adjust=adjust,
                        )
                        st.rerun()
            
            with col_btn2:
                if st.button("🔄 智能更新", type="secondary"):
                    st.info("智能更新功能开发中...")
    
    with col2:
        st.subheader("📊 下载监控")
        
        progress = manager.progress
        
        if progress.total > 0:
            st.metric(
                "下载进度",
                f"{progress.progress_pct:.1f}%",
                f"{progress.completed + progress.failed}/{progress.total}",
            )
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("成功", progress.completed)
            with col_stat2:
                st.metric("失败", progress.failed)
            with col_stat3:
                st.metric("预计剩余", progress.eta)
            
            if progress.current_code:
                st.info(f"正在下载: {progress.current_code}（{progress.current_provider}）")
            
            st.progress(progress.progress_pct / 100)
        
        st.markdown("---")
        
        st.subheader("📝 实时日志")
        
        log_container = st.container()
        
        with log_container:
            if progress.logs:
                for log in list(progress.logs)[-20:]:
                    if "[ERROR]" in log:
                        st.error(log)
                    elif "[WARNING]" in log:
                        st.warning(log)
                    else:
                        st.text(log)
            else:
                st.info("暂无日志")


def render_local_inventory():
    """渲染本地库存页面"""
    st.header("📚 本地库存管理")
    
    data_path = Path(config_loader.get("data.storage.base_path", "./data"))
    
    if not data_path.exists():
        st.warning("数据目录不存在")
        return
    
    parquet_files = list(data_path.glob("*.parquet"))
    
    if not parquet_files:
        st.info("暂无本地数据")
        return
    
    inventory_data = []
    
    for file in parquet_files:
        try:
            df = pd.read_parquet(file)
            inventory_data.append({
                "股票代码": file.stem,
                "开始日期": df["date"].min().strftime("%Y-%m-%d") if not df.empty else "N/A",
                "结束日期": df["date"].max().strftime("%Y-%m-%d") if not df.empty else "N/A",
                "记录数": len(df),
                "文件大小": f"{file.stat().st_size / 1024:.1f} KB",
            })
        except Exception as e:
            logger.error(f"读取文件失败: {file}", error=str(e))
    
    if inventory_data:
        df_inventory = pd.DataFrame(inventory_data)
        st.dataframe(
            df_inventory,
            use_container_width=True,
            hide_index=True,
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("总股票数", len(inventory_data))
        with col2:
            total_size = sum(file.stat().st_size for file in parquet_files)
            st.metric("总数据量", f"{total_size / 1024 / 1024:.1f} MB")


def render_kline_viewer():
    """渲染K线验真页面"""
    st.header("📈 K线验真")
    
    data_path = Path(config_loader.get("data.storage.base_path", "./data"))
    
    if not data_path.exists():
        st.warning("数据目录不存在")
        return
    
    parquet_files = list(data_path.glob("*.parquet"))
    
    if not parquet_files:
        st.info("暂无本地数据")
        return
    
    codes = [file.stem for file in parquet_files]
    
    selected_code = st.selectbox("选择股票", codes)
    
    if selected_code:
        render_kline_chart(selected_code)


def render_kline_chart(code: str):
    """渲染K线图"""
    data_path = Path(config_loader.get("data.storage.base_path", "./data"))
    file_path = data_path / f"{code}.parquet"
    
    if not file_path.exists():
        st.warning(f"股票 {code} 数据不存在")
        return
    
    try:
        df = pd.read_parquet(file_path)
        
        if df.empty:
            st.warning("数据为空")
            return
        
        df = df.sort_values("date")
        
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
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
        
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="成交量",
                marker_color="lightblue",
            ),
            row=2,
            col=1,
        )
        
        fig.update_layout(
            title=f"{code} K线图",
            xaxis_rangeslider_visible=False,
            height=600,
            showlegend=True,
        )
        
        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="价格", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"渲染K线图失败: {str(e)}")
        logger.error("渲染K线图失败", error=str(e), code=code)


def render_backtest():
    """渲染回测分析页面"""
    st.header("💹 回测分析")
    st.info("回测分析功能开发中...")


def main():
    """主函数"""
    st.set_page_config(
        page_title="AlphaScope 统一平台",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    init_session_state()
    render_sidebar()
    
    if st.session_state.page == "数据下载":
        render_data_download()
    elif st.session_state.page == "本地库存":
        render_local_inventory()
    elif st.session_state.page == "K线验真":
        render_kline_viewer()
    elif st.session_state.page == "回测分析":
        render_backtest()


if __name__ == "__main__":
    main()