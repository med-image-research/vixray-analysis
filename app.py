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

    if "pending_tab_switch" in st.session_state:
        st.session_state["active_main_tab"] = st.session_state.pop("pending_tab_switch")
        st.session_state["case_table_selection"] = {
            "selection": {"rows": [], "columns": [], "cells": []}
        }
    elif "active_main_tab" not in st.session_state:
        st.session_state["active_main_tab"] = "Tổng quan"

    tabs = st.tabs(
        [
            "Tổng quan",
            "Danh sách gán nhãn",
            "Chi tiết ca bệnh",
        ],
        key="active_main_tab",
        on_change="rerun",
    )

    with tabs[0]:
        overview.render(filtered)

    with tabs[1]:
        reference_findings.render(data, filtered, store)

    with tabs[2]:
        case_viewer.render(data, filtered, store)


if __name__ == "__main__":
    main()
