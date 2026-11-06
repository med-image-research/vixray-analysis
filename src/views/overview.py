from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import (
    age_distribution_chart,
    age_group_trend_chart,
    comorbidity_distribution_chart,
    cooccurrence_pairs_chart,
    pathology_prevalence_chart,
    sex_distribution_chart,
    split_bar_chart,
    status_donut_chart,
    view_distribution_chart,
)
from src.models import FilteredBundle
from src.pathology import (
    compute_age_group_trends,
    compute_comorbidity_distribution,
    compute_cooccurrence_pairs,
    compute_pathology_statistics,
    get_pathology_labels,
)


def render(filtered: FilteredBundle) -> None:
    """Render the Overview Dashboard with clean metrics, charts, and pathology summary."""
    st.subheader("Tổng quan dữ liệu")
    st.caption("Thống kê tiến độ gán nhãn, thông tin ca chụp và các bệnh lý ghi nhận.")

    master = filtered.master
    annotations = filtered.annotations

    if master.empty:
        st.info("Không có ca bệnh nào phù hợp với bộ lọc hiện tại.")
        return

    total_images = len(master)
    total_findings = len(annotations)

    status_counts = (
        annotations["status"].value_counts().to_dict()
        if not annotations.empty and "status" in annotations.columns
        else {}
    )

    annotated = status_counts.get("Annotated", 0)
    pending = status_counts.get("Pending", 0)

    annotated_images_count = (
        annotations["image_id"].nunique()
        if not annotations.empty and "image_id" in annotations.columns
        else 0
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Tổng số ảnh", f"{total_images:,}")
    col2.metric("Ảnh cần annotate", f"{annotated_images_count:,}")
    col3.metric("Số Reference Finding", f"{total_findings:,}")
    col4.metric("Đã annotate", f"{annotated:,}")
    col5.metric("Chờ xử lý", f"{pending:,}")

    st.markdown("---")
    st.markdown("#### Tiến độ gán nhãn và phân bố tập dữ liệu")
    r1_col1, r1_col2 = st.columns(2)

    with r1_col1:
        fig_status = status_donut_chart(annotations)
        if fig_status:
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Chưa có Reference Finding nào được tạo cho tập dữ liệu này.")

    with r1_col2:
        fig_split = split_bar_chart(master)
        if fig_split:
            st.plotly_chart(fig_split, use_container_width=True)
        else:
            st.info("Không có dữ liệu phân bố tập dữ liệu.")

    st.markdown("---")
    st.markdown("#### Thông tin bệnh nhân và hướng chụp")
    r2_col1, r2_col2, r2_col3 = st.columns([1.2, 0.9, 1.1])

    with r2_col1:
        fig_age = age_distribution_chart(master)
        if fig_age:
            st.plotly_chart(fig_age, use_container_width=True)
        else:
            st.info("Không có dữ liệu độ tuổi.")

    with r2_col2:
        fig_sex = sex_distribution_chart(master)
        if fig_sex:
            st.plotly_chart(fig_sex, use_container_width=True)
        else:
            st.info("Không có dữ liệu giới tính.")

    with r2_col3:
        fig_view = view_distribution_chart(master)
        if fig_view:
            st.plotly_chart(fig_view, use_container_width=True)
        else:
            st.info("Không có dữ liệu hướng chụp.")

    st.markdown("---")
    st.markdown("#### Thống kê bệnh lý và các bệnh hay đi kèm")

    label_df = get_pathology_labels(master)

    if not label_df.empty:
        stats_df = compute_pathology_statistics(master, label_df)
        pairs_df = compute_cooccurrence_pairs(label_df, total_images)
        trend_data = compute_age_group_trends(master, label_df)
        comorb_data = compute_comorbidity_distribution(label_df)

        normal_cases = int((label_df.sum(axis=1) == 0).sum())
        positive_cases = total_images - normal_cases
        positive_rate = (positive_cases / total_images * 100.0) if total_images > 0 else 0.0
        total_labels = int(label_df.sum().sum())
        avg_labels = (total_labels / total_images) if total_images > 0 else 0.0

        pk1, pk2, pk3, pk4 = st.columns(4)
        pk1.metric("Ca có bệnh", f"{positive_cases:,} ({positive_rate:.1f}%)")
        pk2.metric("Ca bình thường", f"{normal_cases:,} ({100 - positive_rate:.1f}%)")
        pk3.metric("Tổng số bệnh ghi nhận", f"{total_labels:,}")
        pk4.metric("Trung bình mỗi ca", f"{avg_labels:.1f} bệnh")

        p_row1_col1, p_row1_col2 = st.columns([1.25, 1.0])
        with p_row1_col1:
            fig_prev = pathology_prevalence_chart(stats_df)
            if fig_prev:
                st.plotly_chart(fig_prev, use_container_width=True)

        with p_row1_col2:
            fig_comorb = comorbidity_distribution_chart(comorb_data)
            if fig_comorb:
                st.plotly_chart(fig_comorb, use_container_width=True)

        p_row2_col1, p_row2_col2 = st.columns([1.0, 1.25])
        with p_row2_col1:
            fig_pairs = cooccurrence_pairs_chart(pairs_df, top_k=8)
            if fig_pairs:
                st.plotly_chart(fig_pairs, use_container_width=True)

        with p_row2_col2:
            fig_trend = age_group_trend_chart(trend_data)
            if fig_trend:
                st.plotly_chart(fig_trend, use_container_width=True)

        with st.expander("Xem bảng chi tiết các bệnh lý"):
            display_stats = stats_df.drop(columns=["Tên gọn"], errors="ignore")
            st.dataframe(display_stats, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Danh sách file dữ liệu và thống kê ca bệnh")
    if "source_file" in master.columns and not master.empty:
        summary_df = (
            master.groupby(["split", "source_file"])
            .agg(Total_Images=("image_id", "count"))
            .reset_index()
            .rename(
                columns={
                    "split": "Tập dữ liệu",
                    "source_file": "File nguồn",
                    "Total_Images": "Tổng số ảnh",
                }
            )
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
