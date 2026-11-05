from __future__ import annotations

from typing import Any
import streamlit as st

from src.models import DatasetBundle, FilterSelection

APP_CSS = """
<style>
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
}

div[data-testid="stMetric"] {
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 12px 14px;
    background-color: #FFFFFF;
}

div[data-testid="stMetric"] label {
    font-size: 0.84rem;
    color: #64748B;
}

[data-tag],
[data-baseweb="tag"],
[data-testid="stMultiSelectTagsContainer"] [data-tag],
div[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: #000000 !important;
    background: #000000 !important;
    color: #FFFFFF !important;
    border-radius: 4px !important;
    border: 1px solid #000000 !important;
}

[data-tag] *,
[data-baseweb="tag"] *,
[data-testid="stMultiSelectTagsContainer"] * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
}

[data-tag]:hover,
[data-baseweb="tag"]:hover {
    background-color: #1E293B !important;
}

.status-badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.78rem;
    font-weight: 600;
}
.status-pending { background-color: #FEF3C7; color: #92400E; }
.status-annotated { background-color: #DCFCE7; color: #166534; }
.status-reviewed { background-color: #E0F2FE; color: #075985; }
.status-notsuitable { background-color: #FEE2E2; color: #991B1B; }

.small-note { color: #64748B; font-size: 0.9rem; }
.section-note { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; }

.clinical-card {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 12px;
}
.clinical-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.clinical-body {
    font-size: 0.92rem;
    color: #0F172A;
    line-height: 1.5;
}

.stCanvas,
div[data-testid="stCanvas"],
div[data-testid="stCanvas"] canvas,
iframe[title*="st_canvas"] {
    cursor: crosshair !important;
}
div[data-testid="stCanvas"] {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    background-color: #000000;
}
</style>
"""


def configure_page() -> None:
    """Set up page layout, title, and theme."""
    st.set_page_config(
        page_title="Không gian gán nhãn ViX-Ray",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_sidebar(
    data: DatasetBundle,
    store: Any = None,
) -> FilterSelection:
    """Render sidebar filters and sync actions."""
    with st.sidebar:
        st.markdown(APP_CSS, unsafe_allow_html=True)
        st.subheader("Bộ lọc dữ liệu")

        master = data.master
        split_order = ["train", "val", "test"]
        available_splits = [s for s in split_order if s in master["split"].unique()] if "split" in master.columns else []
        if not available_splits and "split" in master.columns:
            available_splits = sorted(master["split"].dropna().astype(str).unique())

        available_sexes = sorted(master["sex"].dropna().astype(str).unique()) if "sex" in master.columns else []
        available_views = sorted(master["view"].dropna().astype(str).unique()) if "view" in master.columns else []

        if "filter_splits" not in st.session_state:
            st.session_state["filter_splits"] = available_splits
        if "filter_sexes" not in st.session_state:
            st.session_state["filter_sexes"] = available_sexes
        if "filter_views" not in st.session_state:
            st.session_state["filter_views"] = available_views

        splits = st.multiselect("Tập dữ liệu", options=available_splits, key="filter_splits")
        sexes = st.multiselect("Giới tính", options=available_sexes, key="filter_sexes")
        views = st.multiselect("Hướng chụp", options=available_views, key="filter_views")

        def _reset_filters() -> None:
            st.session_state["filter_splits"] = available_splits
            st.session_state["filter_sexes"] = available_sexes
            st.session_state["filter_views"] = available_views

        st.button("Đặt lại bộ lọc", on_click=_reset_filters, use_container_width=True)
        st.divider()

        if store is not None and getattr(store, "is_sheets_connected", False):
            st.caption("🟢 **Google Sheets**: Đã kết nối")
            if st.button("🔄 Đồng bộ dữ liệu mới", use_container_width=True, help="Tải lại toàn bộ dữ liệu mới nhất từ Google Sheets"):
                store.get_annotations(force_refresh=True)
                st.cache_data.clear()
                st.rerun()
        else:
            st.caption("📁 **Lưu trữ**: Tệp cục bộ")

        st.caption("Bộ lọc áp dụng cho tất cả các màn hình hiển thị.")

    return FilterSelection(
        splits=tuple(splits),
        sexes=tuple(sexes),
        views=tuple(views),
    )
