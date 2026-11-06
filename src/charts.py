from __future__ import annotations

from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import STATUS_DISPLAY_MAP
from src.pathology import SYSTEM_COLORS

SPLIT_ORDER = ("train", "val", "test")

STATUS_COLOR_MAP = {
    "Đã annotate": "#22C55E",
    "Đã kiểm duyệt": "#0EA5E9",
    "Chờ xử lý": "#F59E0B",
    "Không phù hợp": "#EF4444",
    "Annotated": "#22C55E",
    "Reviewed": "#0EA5E9",
    "Pending": "#F59E0B",
    "Not suitable": "#EF4444",
}

SEX_COLOR_MAP = {
    "Nam": "#3B82F6",
    "Nữ": "#EC4899",
    "Chưa rõ": "#94A3B8",
}


def apply_chart_style(fig: go.Figure) -> go.Figure:
    """Apply clean, minimal chart styling matching modern dashboard standards."""
    fig.update_layout(
        margin=dict(l=10, r=20, t=44, b=10),
        title_x=0,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#1E293B", size=12),
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E2E8F0")
    return fig


def status_donut_chart(annotations: pd.DataFrame) -> go.Figure | None:
    """Build a donut chart of reference finding annotation statuses."""
    if annotations.empty or "status" not in annotations.columns:
        return None

    counts = annotations["status"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    counts["status"] = counts["status"].map(STATUS_DISPLAY_MAP).fillna(counts["status"])

    fig = px.pie(
        counts,
        values="count",
        names="status",
        color="status",
        color_discrete_map=STATUS_COLOR_MAP,
        hole=0.48,
        title="Tỷ lệ trạng thái gán nhãn",
    )
    return apply_chart_style(fig)


def split_bar_chart(master: pd.DataFrame) -> go.Figure | None:
    """Build a bar chart of cases distributed across splits."""
    if master.empty or "split" not in master.columns:
        return None

    counts = (
        master["split"]
        .value_counts()
        .reindex(list(SPLIT_ORDER))
        .fillna(0)
        .reset_index()
    )
    counts.columns = ["split", "images"]

    fig = px.bar(
        counts,
        x="split",
        y="images",
        text_auto=True,
        title="Phân bố theo tập dữ liệu",
        labels={"split": "Tập dữ liệu", "images": "Số lượng ảnh"},
        color="split",
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    return apply_chart_style(fig)


def age_distribution_chart(master: pd.DataFrame) -> go.Figure | None:
    """Build a histogram of patient age distribution."""
    if master.empty or "age" not in master.columns:
        return None

    numeric_ages = pd.to_numeric(master["age"], errors="coerce").dropna()
    if numeric_ages.empty:
        return None

    df_age = pd.DataFrame({"age": numeric_ages})
    fig = px.histogram(
        df_age,
        x="age",
        nbins=25,
        title="Phân bố độ tuổi",
        labels={"age": "Tuổi", "count": "Số lượng ca"},
        color_discrete_sequence=["#2563EB"],
    )
    fig.update_layout(bargap=0.08)
    return apply_chart_style(fig)


def sex_distribution_chart(master: pd.DataFrame) -> go.Figure | None:
    """Build a donut chart of patient gender distribution."""
    if master.empty or "sex" not in master.columns:
        return None

    counts = master["sex"].fillna("Chưa rõ").value_counts().reset_index()
    counts.columns = ["sex", "count"]

    fig = px.pie(
        counts,
        values="count",
        names="sex",
        color="sex",
        color_discrete_map=SEX_COLOR_MAP,
        hole=0.48,
        title="Tỷ lệ giới tính",
    )
    return apply_chart_style(fig)


def view_distribution_chart(master: pd.DataFrame) -> go.Figure | None:
    """Build a bar chart of X-ray projection view positions."""
    if master.empty or "view" not in master.columns:
        return None

    counts = master["view"].fillna("Chưa rõ").value_counts().reset_index()
    counts.columns = ["view", "images"]

    fig = px.bar(
        counts,
        x="view",
        y="images",
        text_auto=True,
        title="Phân bố hướng chụp",
        labels={"view": "Hướng chụp", "images": "Số lượng ca"},
        color="view",
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    return apply_chart_style(fig)


def pathology_prevalence_chart(stats_df: pd.DataFrame) -> go.Figure | None:
    """Build clean horizontal bar chart of 14 abnormality groups across 4 organ systems."""
    if stats_df.empty or "Tên gọn" not in stats_df.columns:
        return None

    plot_df = stats_df.iloc[::-1].copy()
    cnt_series = plot_df["Số ca"] if "Số ca" in plot_df.columns else plot_df.get("Số lượng ca", pd.Series(dtype=int))
    pct_series = (
        plot_df["Tỷ lệ P(Bệnh) (%)"]
        if "Tỷ lệ P(Bệnh) (%)" in plot_df.columns
        else plot_df.get("Tỷ lệ (%)", pd.Series(dtype=float))
    )

    plot_df["label"] = [
        f"{c:,} ca ({p:.2f}%)" if isinstance(p, (int, float)) else f"{c:,} ca"
        for c, p in zip(cnt_series, pct_series)
    ]

    fig = px.bar(
        plot_df,
        x=cnt_series.name,
        y="Tên gọn",
        color="Hệ cơ quan",
        color_discrete_map=SYSTEM_COLORS,
        orientation="h",
        text="label",
        title="14 nhóm bất thường thường gặp nhất",
        labels={cnt_series.name: "Số ca", "Tên": ""},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    max_val = max(cnt_series) if not cnt_series.empty else 100
    fig.update_layout(
        xaxis=dict(range=[0, max_val * 1.30], showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(showgrid=False),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.16,
            xanchor="left",
            x=0,
            title=None,
        ),
        margin=dict(l=10, r=30, t=40, b=50),
        height=520,
    )
    return apply_chart_style(fig)


def cooccurrence_pairs_chart(pairs_df: pd.DataFrame, top_k: int = 8) -> go.Figure | None:
    """Build clean horizontal bar chart of top co-occurring disease pairs."""
    if pairs_df.empty:
        return None

    top_pairs = pairs_df.head(top_k).iloc[::-1].copy()
    cnt_col = "Số ca đồng mắc" if "Số ca đồng mắc" in top_pairs.columns else "Số ca cùng gặp"
    pct_col = "Xác suất đồng mắc (%)" if "Xác suất đồng mắc (%)" in top_pairs.columns else "Tỷ lệ gặp cả hai (%)"
    pair_col = "Cặp bệnh lý đồng mắc" if "Cặp bệnh lý đồng mắc" in top_pairs.columns else "Cặp bệnh hay đi kèm"

    top_pairs["label"] = [
        f"{c:,} ca ({p:.2f}%)" if isinstance(p, (int, float)) else f"{c:,} ca"
        for c, p in zip(top_pairs[cnt_col], top_pairs[pct_col])
    ]

    fig = px.bar(
        top_pairs,
        x=cnt_col,
        y=pair_col,
        orientation="h",
        text="label",
        color_discrete_sequence=["#2563EB"],
        title=f"Top {len(top_pairs)} cặp bệnh lý đồng mắc phổ biến nhất — P(A ∩ B)",
        labels={cnt_col: "Số ca đồng mắc", pair_col: ""},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    max_val = max(top_pairs[cnt_col]) if not top_pairs.empty else 100
    fig.update_layout(
        xaxis=dict(range=[0, max_val * 1.25], showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(showgrid=False),
        margin=dict(l=10, r=30, t=40, b=20),
        height=400,
    )
    return apply_chart_style(fig)


def age_group_trend_chart(trend_data: dict[str, Any]) -> go.Figure | None:
    """Build clean line chart showing pathology rates across age groups without visual clutter."""
    if not trend_data or "series" not in trend_data or not trend_data["series"]:
        return None

    fig = go.Figure()
    for item in trend_data["series"]:
        fig.add_trace(
            go.Scatter(
                x=trend_data["age_labels"],
                y=item["rates"],
                mode="lines+markers",
                name=item["short_name"],
                line=dict(color=item["color"], width=2.5),
                marker=dict(symbol=item["marker"], size=8),
                hovertemplate="<b>%{data.name}</b><br>Độ tuổi: %{x}<br>Tỷ lệ: %{y:.1f}%<extra></extra>",
            )
        )

    fig.update_layout(
        title="Tỷ lệ bệnh theo từng độ tuổi",
        xaxis=dict(title="Độ tuổi", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(
            title="Tỷ lệ ca (%)",
            range=[-2, 102],
            showgrid=True,
            gridcolor="#E2E8F0",
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="left",
            x=0,
            title=None,
            font=dict(size=11),
        ),
        margin=dict(l=10, r=20, t=40, b=50),
        height=400,
    )
    return apply_chart_style(fig)


def comorbidity_distribution_chart(
    comorb_data: list[tuple[str, int, str, float]],
) -> go.Figure | None:
    """Build clean bar chart of number of diseases found per chest X-ray image."""
    if not comorb_data:
        return None

    x_labels = [item[0] for item in comorb_data]
    y_counts = [item[1] for item in comorb_data]
    colors = [item[2] for item in comorb_data]
    pcts = [item[3] for item in comorb_data]
    texts = [f"{c:,} ca ({p:.1f}%)" for c, p in zip(y_counts, pcts)]

    fig = go.Figure(
        go.Bar(
            x=x_labels,
            y=y_counts,
            marker_color=colors,
            text=texts,
            textposition="outside",
            cliponaxis=False,
        )
    )

    max_val = max(y_counts) if y_counts else 100
    fig.update_layout(
        title="Số lượng bệnh trên mỗi ca chụp",
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(
            title="Số ca chụp",
            range=[0, max_val * 1.2],
            showgrid=True,
            gridcolor="#E2E8F0",
        ),
        margin=dict(l=10, r=10, t=40, b=30),
        height=480,
    )
    return apply_chart_style(fig)
