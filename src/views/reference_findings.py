from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
import streamlit as st

from src.models import DatasetBundle, FilteredBundle
from src.storage import GoogleSheetsStore

DISPLAY_COLUMNS = [
    "image_id",
    "split",
    "view",
    "sex",
    "age",
    "total_findings",
    "pending_findings",
    "annotated_findings",
    "case_status",
]

COLUMN_LABELS = {
    "image_id": "Mã ảnh",
    "split": "Tập dữ liệu",
    "view": "Hướng chụp",
    "sex": "Giới tính",
    "age": "Tuổi",
    "total_findings": "Tổng số Reference Finding",
    "pending_findings": "Chưa annotate",
    "annotated_findings": "Đã annotate",
    "case_status": "Trạng thái",
}


@st.cache_data(show_spinner=False)
def calculate_case_summary(master: pd.DataFrame, annotations: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-case reference finding counts and annotation status."""
    df = master.copy()
    if annotations.empty or "image_id" not in annotations.columns:
        df["total_findings"] = 0
        df["annotated_findings"] = 0
        df["pending_findings"] = 0
        df["case_status"] = "Không annotate"
        return df

    annot = annotations.copy()
    annot["is_annotated"] = annot["status"].isin([
        "Annotated", "Reviewed", "Đã annotate", "Đã kiểm duyệt"
    ])
    annot["is_pending"] = ~annot["is_annotated"]

    agg = (
        annot.groupby("image_id")
        .agg(
            total_findings=("status", "count"),
            annotated_findings=("is_annotated", "sum"),
            pending_findings=("is_pending", "sum"),
        )
        .reset_index()
    )

    df = df.merge(agg, on="image_id", how="left")
    df["total_findings"] = df["total_findings"].fillna(0).astype(int)
    df["annotated_findings"] = df["annotated_findings"].fillna(0).astype(int)
    df["pending_findings"] = df["pending_findings"].fillna(0).astype(int)

    conditions = [
        df["total_findings"] == 0,
        df["pending_findings"] == 0,
        df["annotated_findings"] > 0,
    ]
    choices = [
        "Không annotate",
        "Đã annotate",
        "Đang annotate",
    ]
    df["case_status"] = np.select(conditions, choices, default="Chưa annotate")
    return df


def filter_cases(
    cases: pd.DataFrame,
    rf_count: str,
    status: str,
    split: str,
    keyword: str,
) -> pd.DataFrame:
    """Filter cases by finding count, status, dataset split, and search term."""
    df = cases.copy()
    if rf_count != "Tất cả":
        df = df[df["total_findings"] == int(rf_count)]

    if status != "Tất cả":
        df = df[df["case_status"] == status]

    if split != "Tất cả":
        df = df[df["split"] == split]

    if keyword.strip():
        kw = keyword.strip().lower()
        search_mask = (
            df["image_id"].astype(str).str.lower().str.contains(kw)
            | df.get("findings", pd.Series([""] * len(df))).astype(str).str.lower().str.contains(kw)
            | df.get("impressions", pd.Series([""] * len(df))).astype(str).str.lower().str.contains(kw)
        )
        df = df[search_mask]

    return df


def extract_selected_case_id(selection_event: Any, cases: pd.DataFrame) -> str | None:
    """Extract image_id from dataframe single-cell or row click event."""
    if not selection_event:
        return None

    selected_cells = []
    selected_rows = []
    if hasattr(selection_event, "selection"):
        selected_cells = getattr(selection_event.selection, "cells", [])
        selected_rows = getattr(selection_event.selection, "rows", [])
    elif isinstance(selection_event, dict) and "selection" in selection_event:
        selected_cells = selection_event["selection"].get("cells", [])
        selected_rows = selection_event["selection"].get("rows", [])

    row_idx = None
    if selected_cells:
        row_idx = selected_cells[0][0]
    elif selected_rows:
        row_idx = selected_rows[0]

    if row_idx is not None and 0 <= row_idx < len(cases):
        return str(cases.iloc[row_idx]["image_id"])
    return None


def render(
    data: DatasetBundle | Any,
    filtered: FilteredBundle | pd.DataFrame | None = None,
    store: GoogleSheetsStore | None = None,
    **kwargs: Any,
) -> None:
    """Render the 5,400 Case Explorer and Annotation Management tab."""
    st.subheader("Danh sách ca bệnh và trạng thái gán nhãn")
    st.caption("Quản lý toàn bộ 5.400 ca bệnh ViX-Ray, theo dõi số lượng Reference Finding và tiến độ khoanh vùng.")

    if isinstance(data, DatasetBundle):
        annotations = data.annotations
        master = filtered.master if isinstance(filtered, FilteredBundle) else data.master
    else:
        annotations = getattr(data, "annotations", pd.DataFrame())
        master = filtered if isinstance(filtered, pd.DataFrame) else getattr(data, "master", pd.DataFrame())

    if master.empty:
        st.info("Không có ca bệnh nào phù hợp với bộ lọc hiện tại.")
        return

    case_summary = calculate_case_summary(master, annotations)

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1.2, 1, 2])
    with col_f1:
        unique_counts = sorted(list(case_summary["total_findings"].unique()))
        rf_count = st.selectbox(
            "Tổng số Reference Finding",
            ["Tất cả"] + [str(c) for c in unique_counts],
            index=0,
            key="case_tab_rf_count_filter",
        )
    with col_f2:
        status = st.selectbox(
            "Lọc trạng thái gán nhãn",
            ["Tất cả", "Đã annotate", "Đang annotate", "Chưa annotate", "Không annotate"],
            index=0,
            key="case_tab_status_filter",
        )
    with col_f3:
        available_splits = ["Tất cả"] + sorted([
            str(s) for s in case_summary["split"].dropna().unique() if str(s)
        ])
        split = st.selectbox(
            "Lọc tập dữ liệu",
            available_splits,
            index=0,
            key="case_tab_split_filter",
        )
    with col_f4:
        keyword = st.text_input(
            "Tìm kiếm ca bệnh",
            value="",
            placeholder="Tìm theo mã ảnh, mô tả hình ảnh, kết luận chẩn đoán...",
            key="case_tab_search_filter",
        )

    filtered_cases = filter_cases(case_summary, rf_count, status, split, keyword)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Số ảnh hiển thị", f"{len(filtered_cases):,}")
    m2.metric("Tổng số Reference Finding", f"{int(filtered_cases['total_findings'].sum()):,}")
    m3.metric("Đã annotate", f"{len(filtered_cases[filtered_cases['case_status'] == 'Đã annotate']):,}")
    m4.metric("Không annotate", f"{len(filtered_cases[filtered_cases['case_status'] == 'Không annotate']):,}")

    st.markdown("---")
    st.caption("Nhấp vào bất kỳ dòng nào trong bảng để mở ngay chi tiết và gán nhãn ca bệnh đó.")

    present_cols = [c for c in DISPLAY_COLUMNS if c in filtered_cases.columns]
    sorted_cases = filtered_cases.sort_values("image_id").copy()
    table_df = sorted_cases[present_cols].rename(columns=COLUMN_LABELS)

    selection_event = st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-cell",
        key="case_table_selection",
    )

    clicked_id = extract_selected_case_id(selection_event, sorted_cases)
    if clicked_id:
        all_ids = sorted(master["image_id"].dropna().unique().tolist())
        if clicked_id in all_ids:
            st.session_state.current_case_idx = all_ids.index(clicked_id)
            st.session_state["target_case_id"] = clicked_id
            st.query_params["tab"] = "case-viewer"
            st.query_params["case"] = clicked_id
            st.session_state["pending_tab_switch"] = "Chi tiết ca bệnh"
            st.rerun()
