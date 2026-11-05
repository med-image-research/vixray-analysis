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

    TAB_NAMES = ["Tổng quan", "Danh sách gán nhãn", "Chi tiết ca bệnh"]
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
        target_tab = st.session_state.pop("pending_tab_switch")
        st.session_state["main_tab_nav"] = target_tab
        st.session_state["case_table_selection"] = {
            "selection": {"rows": [], "columns": [], "cells": []}
        }
    elif "_last_seen_url_tab" not in st.session_state or st.session_state["_last_seen_url_tab"] != query_tab:
        st.session_state["_last_seen_url_tab"] = query_tab
        if query_case:
            st.session_state["main_tab_nav"] = "Chi tiết ca bệnh"
        elif query_tab in SLUG_TAB_MAP:
            st.session_state["main_tab_nav"] = SLUG_TAB_MAP[query_tab]
        elif "main_tab_nav" not in st.session_state:
            st.session_state["main_tab_nav"] = "Tổng quan"

    if "main_tab_nav" not in st.session_state or st.session_state["main_tab_nav"] not in TAB_NAMES:
        st.session_state["main_tab_nav"] = "Tổng quan"

    current_idx = TAB_NAMES.index(st.session_state["main_tab_nav"])

    # Modern styled navigation tabs
    st.markdown(
        """
        <style>
        div.st-key-main_tab_nav {
            margin-bottom: 1.5rem;
        }
        div.st-key-main_tab_nav div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            gap: 8px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0px;
        }
        div.st-key-main_tab_nav div[role="radiogroup"] label {
            margin: 0;
            padding: 10px 24px;
            border-radius: 8px 8px 0 0;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            background: transparent;
            border: 1px solid transparent;
            border-bottom: none;
            color: #64748b;
            transition: all 0.15s ease-in-out;
        }
        div.st-key-main_tab_nav div[role="radiogroup"] label:hover {
            background: #f8fafc;
            color: #1e293b;
        }
        div.st-key-main_tab_nav div[role="radiogroup"] label:has(input:checked) {
            background: #ffffff !important;
            color: #2563eb !important;
            border-color: #cbd5e1 !important;
            border-bottom: 2px solid #2563eb !important;
            margin-bottom: -2px;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.02);
        }
        div.st-key-main_tab_nav div[role="radiogroup"] input[type="radio"],
        div.st-key-main_tab_nav div[role="radiogroup"] div[data-testid="stRadioOptionCircle"] {
            display: none !important;
        }
        @media (prefers-color-scheme: dark) {
            div.st-key-main_tab_nav div[role="radiogroup"] {
                border-bottom-color: #334155;
            }
            div.st-key-main_tab_nav div[role="radiogroup"] label {
                color: #94a3b8;
            }
            div.st-key-main_tab_nav div[role="radiogroup"] label:hover {
                background: #1e293b;
                color: #f1f5f9;
            }
            div.st-key-main_tab_nav div[role="radiogroup"] label:has(input:checked) {
                background: #0f172a !important;
                color: #60a5fa !important;
                border-color: #334155 !important;
                border-bottom: 2px solid #60a5fa !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    active_tab = st.radio(
        "Navigation",
        TAB_NAMES,
        index=current_idx,
        horizontal=True,
        label_visibility="collapsed",
        key="main_tab_nav",
    )

    desired_slug = TAB_SLUG_MAP.get(active_tab, "overview")
    if st.query_params.get("tab") != desired_slug:
        st.query_params["tab"] = desired_slug
        st.session_state["_last_seen_url_tab"] = desired_slug

    if active_tab != "Chi tiết ca bệnh" and "case" in st.query_params:
        del st.query_params["case"]

    if active_tab == "Tổng quan":
        overview.render(filtered)
    elif active_tab == "Danh sách gán nhãn":
        reference_findings.render(data, filtered, store)
    elif active_tab == "Chi tiết ca bệnh":
        case_viewer.render(data, filtered, store)


if __name__ == "__main__":
    main()
