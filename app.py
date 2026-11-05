from __future__ import annotations

import streamlit as st

from src import patch  # noqa: F401 - Streamlit backward compatibility
from src.data import load_data
from src.filters import apply_filters
from src.storage import GoogleSheetsStore
from src.ui import configure_page, render_sidebar
from src.views import case_viewer, overview, reference_findings


@st.cache_resource(show_spinner="Đang kết nối cơ sở dữ liệu...")
def get_store() -> GoogleSheetsStore:
    return GoogleSheetsStore()


def main() -> None:
    configure_page()

    st.title("Không gian gán nhãn ViX-Ray")
    st.caption("Hệ thống nghiên cứu và gán nhãn không gian cho ảnh X-quang ngực ViX-Ray.")

    try:
        store = get_store()
        data = load_data(store)
    except Exception as exc:
        st.error(f"Lỗi nạp dữ liệu: {exc}")
        st.stop()

    selection = render_sidebar(data, store)
    filtered = apply_filters(data, selection)

    TAB_NAMES = [
        "Tổng quan",
        "Danh sách gán nhãn",
        "Chi tiết ca bệnh",
    ]
    TAB_SLUG_MAP = {
        "Tổng quan": "overview",
        "Danh sách gán nhãn": "findings",
        "Chi tiết ca bệnh": "case-viewer",
    }
    SLUG_TAB_MAP = {
        "overview": "Tổng quan",
        "findings": "Danh sách gán nhãn",
        "reference-findings": "Danh sách gán nhãn",
        "case-viewer": "Chi tiết ca bệnh",
        "cases": "Chi tiết ca bệnh",
    }

    query_tab = str(st.query_params.get("tab", "")).strip().lower()
    query_case = str(st.query_params.get("case", "") or st.query_params.get("image_id", "")).strip()

    if "pending_tab_switch" in st.session_state:
        st.session_state["active_main_tab"] = st.session_state.pop("pending_tab_switch")
        st.session_state["case_table_selection"] = {
            "selection": {"rows": [], "columns": [], "cells": []}
        }
    elif "active_main_tab" not in st.session_state:
        if query_case:
            st.session_state["active_main_tab"] = "Chi tiết ca bệnh"
        elif query_tab in SLUG_TAB_MAP:
            st.session_state["active_main_tab"] = SLUG_TAB_MAP[query_tab]
        else:
            st.session_state["active_main_tab"] = "Tổng quan"

    target_tab = st.session_state.get("active_main_tab", "Tổng quan")
    if target_tab not in TAB_NAMES:
        target_tab = "Tổng quan"
        st.session_state["active_main_tab"] = target_tab

    try:
        tabs = st.tabs(
            TAB_NAMES,
            key="active_main_tab",
            on_change="rerun",
            default=target_tab,
        )
    except TypeError:
        try:
            tabs = st.tabs(
                TAB_NAMES,
                key="active_main_tab",
                on_change="rerun",
            )
        except TypeError:
            tabs = st.tabs(TAB_NAMES)

    current_tab = st.session_state.get("active_main_tab", "Tổng quan")
    desired_slug = TAB_SLUG_MAP.get(current_tab, "overview")
    if st.query_params.get("tab") != desired_slug:
        st.query_params["tab"] = desired_slug

    if current_tab != "Chi tiết ca bệnh" and "case" in st.query_params:
        del st.query_params["case"]

    with tabs[0]:
        overview.render(filtered)

    with tabs[1]:
        reference_findings.render(data, filtered, store)

    with tabs[2]:
        case_viewer.render(data, filtered, store)


if __name__ == "__main__":
    main()
