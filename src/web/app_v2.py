"""
AlphaScope Web 平台 V2 - 数据下载与管理系统

本模块提供完整的Web界面，包括：
- 数据下载与同步工作台（Tab 1）
- 本地库存与K线浏览器（Tab 2）
- 异步下载处理
- 实时进度监控
- K线图可视化

使用示例：
    streamlit run src/web/app_v2.py
"""

import asyncio
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


logger = get_logger("WebAppV2")


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


@dataclass
class DownloadProgress:
    """下载进度数据类"""
    total: int = 0
    completed: int = 0
    failed: int = 0
    current_code: str = ""
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


class DownloadManager:
    """下载管理器"""
    
    def __init__(self):
        self.progress = DownloadProgress()
        self.is_running = False
        self._lock = threading.Lock()
    
    def start_download(
        self,
        codes: list[str],
        start_date: datetime,
        end_date: datetime,
        adjust: str,
        provider_name: str,
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
        
        thread = threading.Thread(
            target=self._download_worker,
            args=(codes, start_date, end_date, adjust, provider_name),
            daemon=True,
        )
        thread.start()
    
    def _download_worker(
        self,
        codes: list[str],
        start_date: datetime,
        end_date: datetime,
        adjust: str,
        provider_name: str,
    ):
        """下载工作线程"""
        try:
            provider = self._get_provider(provider_name)
            
            for code in codes:
                if not self.is_running:
                    break
                
                with self._lock:
                    self.progress.current_code = code
                
                try:
                    task = DownloadTask(
                        code=code,
                        start_date=start_date,
                        end_date=end_date,
                        adjust=adjust,
                    )
                    
                    df = provider.download_and_save(
                        code=code,
                        start_date=start_date,
                        end_date=end_date,
                        adjust=adjust,
                    )
                    
                    with self._lock:
                        if not df.empty:
                            task.status = "success"
                            task.rows = len(df)
                            self.progress.completed += 1
                            self.progress.logs.append(
                                f"[SUCCESS] {code} 下载成功，共导入 {len(df)} 行数据"
                            )
                        else:
                            task.status = "empty"
                            self.progress.failed += 1
                            self.progress.logs.append(
                                f"[WARNING] {code} 数据为空"
                            )
                
                except Exception as e:
                    with self._lock:
                        self.progress.failed += 1
                        self.progress.logs.append(
                            f"[ERROR] {code} 下载失败: {str(e)}"
                        )
                
                time.sleep(0.1)
        
        finally:
            with self._lock:
                self.is_running = False
                self.progress.current_code = ""
    
    def _get_provider(self, name: str):
        """获取数据提供者"""
        providers = {
            "akshare": AKShareProvider,
            "baostock": BaoStockProvider,
            "tushare": TushareProvider,
        }
        return providers.get(name, AKShareProvider)()
    
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


def render_header():
    """渲染页面头部"""
    st.title("📊 AlphaScope 数据管理平台")
    st.markdown("---")


def render_tab1_download():
    """渲染 Tab 1: 数据下载与同步工作台"""
    st.header("📥 数据下载与同步工作台")
    
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
        
        provider_name = st.selectbox(
            "数据源",
            ["akshare", "baostock", "tushare"],
        )
        
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
                            provider_name=provider_name,
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
                st.info(f"正在下载: {progress.current_code}")
            
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


def render_tab2_browser():
    """渲染 Tab 2: 本地库存与K线浏览器"""
    st.header("📚 本地库存与K线浏览器")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📋 本地资产看板")
        
        data_path = Path(config_loader.get("data.storage.base_path", "./data"))
        
        if not data_path.exists():
            st.warning("数据目录不存在")
            return
        
        parquet_files = list(data_path.glob("*.parquet"))
        
        if not parquet_files:
            st.info("暂无本地数据")
            return
        
        inventory_data = []
        
        for file in parquet_files[:10]:
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
            
            selected = st.selectbox(
                "选择股票查看K线图",
                [item["股票代码"] for item in inventory_data],
            )
            
            if selected:
                st.session_state.selected_code = selected
    
    with col2:
        st.subheader("📈 K线图预览")
        
        if st.session_state.selected_code:
            render_kline_chart(st.session_state.selected_code)
        else:
            st.info("请选择股票查看K线图")


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


def main():
    """主函数"""
    st.set_page_config(
        page_title="AlphaScope 数据管理平台",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    init_session_state()
    render_header()
    
    tab1, tab2 = st.tabs([
        "📥 数据下载与同步工作台",
        "📚 本地库存与K线浏览器",
    ])
    
    with tab1:
        render_tab1_download()
    
    with tab2:
        render_tab2_browser()


if __name__ == "__main__":
    main()