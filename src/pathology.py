from __future__ import annotations

from itertools import combinations
import re
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

ORGAN_SYSTEMS = [
    "Nhu mô phổi",
    "Tim và mạch máu lớn",
    "Màng phổi và vòm hoành",
    "Xương và thành ngực",
]

SYSTEM_COLORS: dict[str, str] = {
    "Nhu mô phổi": "#1E3A8A",
    "Tim và mạch máu lớn": "#E11D48",
    "Màng phổi và vòm hoành": "#0D9488",
    "Xương và thành ngực": "#D97706",
}

SHORT_LABEL_MAP: dict[str, str] = {
    "Tổn thương và dày tổ chức kẽ phổi": "Tổn thương mô kẽ",
    "Bóng tim to và giãn buồng tim": "Tim to, suy tim",
    "Vôi hóa động mạch chủ": "Vôi hóa động mạch chủ",
    "Quai động mạch chủ vồng hoặc giãn": "Quai ĐMC vồng, giãn",
    "Đám mờ và đông đặc phổi": "Đám mờ, đông đặc phổi",
    "Xơ hóa và dải xơ hoặc xẹp phổi": "Xơ hóa, xẹp phổi",
    "Bất thường xương sườn và cột sống": "Bất thường xương, cột sống",
    "Nốt phổi và nốt vôi hóa": "Nốt phổi, vôi hóa",
    "Tù góc sườn hoành": "Tù góc sườn hoành",
    "Tràn dịch màng phổi": "Tràn dịch màng phổi",
    "Dày dính màng phổi và tràn khí màng phổi": "Dày dính, tràn khí MP",
    "Bất thường vòm hoành": "Bất thường vòm hoành",
    "Vật liệu can thiệp và thiết bị y tế": "Vật liệu can thiệp y tế",
    "Khối choán chỗ và bất thường trung thất": "U, hạch, trung thất",
}

TOP5_AGE_TREND_DISEASES: list[tuple[str, str, str, str]] = [
    ("Tổn thương và dày tổ chức kẽ phổi", "Tổn thương mô kẽ", "#1E3A8A", "circle"),
    ("Bóng tim to và giãn buồng tim", "Tim to, suy tim", "#E11D48", "square"),
    ("Vôi hóa động mạch chủ", "Vôi hóa động mạch chủ", "#D97706", "triangle-up"),
    ("Quai động mạch chủ vồng hoặc giãn", "Quai ĐMC vồng, giãn", "#0D9488", "diamond"),
    ("Đám mờ và đông đặc phổi", "Đám mờ, đông đặc phổi", "#7C3AED", "triangle-down"),
]

HIERARCHICAL_TAXONOMY: list[tuple[str, str, list[str]]] = [
    (
        "Nhu mô phổi",
        "Tổn thương và dày tổ chức kẽ phổi",
        [
            r"phổi\s*kẽ",
            r"tổn\s*thương\s*kẽ",
            r"dày\s*(?:nhẹ\s*)?(?:tổ\s*chức\s*)?kẽ",
            r"mờ\s*(?:nốt\s*)?kẽ",
            r"xơ\s*kẽ",
        ],
    ),
    (
        "Tim và mạch máu lớn",
        "Bóng tim to và giãn buồng tim",
        [
            r"bóng\s*(?:mờ\s*)?tim\s*to",
            r"\btim\s*to\b",
            r"tim\s*bè",
            r"các\s*cung\s*tim\s*rộng",
            r"giãn\s*thất",
            r"hình\s*tim\s*treo",
            r"suy\s*tim",
            r"ứ\s*huyết",
            r"tăng\s*tuần\s*hoàn",
            r"tái\s*phân\s*bố\s*tưới\s*máu",
            r"rốn\s*phổi.*tăng\s*đậm",
            r"phù\s*phổi",
            r"tăng\s*áp\s*động\s*mạch\s*phổi",
        ],
    ),
    (
        "Tim và mạch máu lớn",
        "Vôi hóa động mạch chủ",
        [
            r"vôi\s*hóa.*(?:động\s*mạch\s*chủ|đmc|quai)",
            r"xơ\s*vữa.*(?:động\s*mạch\s*chủ|đmc|quai)",
        ],
    ),
    (
        "Tim và mạch máu lớn",
        "Quai động mạch chủ vồng hoặc giãn",
        [
            r"(?:quai|động\s*mạch\s*chủ|đmc).*vồng",
            r"vồng.*(?:quai|động\s*mạch\s*chủ|đmc)",
            r"giãn.*(?:động\s*mạch\s*chủ|đmc)",
        ],
    ),
    (
        "Nhu mô phổi",
        "Đám mờ và đông đặc phổi",
        [
            r"viêm\s*phổi",
            r"td\s*viêm",
            r"theo\s*dõi\s*viêm",
            r"apsxe",
            r"áp\s*xe",
            r"abces",
            r"\bavh\b",
            r"phế\s*quản",
            r"đông\s*đặc",
            r"đám\s*mờ",
            r"mờ\s*kính",
            r"kính\s*mờ",
            r"mờ\s*không\s*đều",
            r"mờ\s*rải\s*rác",
            r"mờ\s*(?:tương\s*đối\s*)?đồng\s*nhất",
            r"mờ\s*(?:vùng\s*)?đáy",
            r"mờ\s*toàn\s*bộ\s*phổi",
            r"tổn\s*thương\s*nhu\s*mô",
            r"thâm\s*nhiễm",
            r"cấu\s*trúc\s*hình\s*hang",
            r"dạng\s*hang",
            r"tổn\s*thương\s*hình\s*hang",
        ],
    ),
    (
        "Nhu mô phổi",
        "Xơ hóa và dải xơ hoặc xẹp phổi",
        [
            r"xơ\s*phổi",
            r"dải\s*xơ",
            r"dải\s*mờ",
            r"mờ\s*dạng\s*dải",
            r"xơ\s*hóa",
            r"xơ\s*mờ",
            r"\blao\b",
            r"xẹp\s*(?:nhẹ\s*)?(?:thùy|thuỳ|phổi)",
            r"(?:đám|dải)\s*xẹp",
            r"co\s*kéo",
            r"khí\s*phế\s*thũng",
            r"khí\s*thũng",
            r"copd",
            r"ứ\s*khí",
            r"giãn\s*phế\s*nang",
            r"quá\s*sáng",
            r"kém\s*sáng",
        ],
    ),
    (
        "Xương và thành ngực",
        "Bất thường xương sườn và cột sống",
        [
            r"cột\s*sống",
            r"\bgãy\b",
            r"xương\s*sườn",
            r"xương\s*đòn",
            r"xương\s*bả\s*vai",
            r"xương\s*vai",
            r"thoái\s*hóa",
            r"đốt\s*sống",
            r"khoang\s*liên\s*sườn\s*hẹp",
        ],
    ),
    (
        "Nhu mô phổi",
        "Nốt phổi và nốt vôi hóa",
        [
            r"nốt\s*mờ",
            r"mờ\s*nốt",
            r"nốt\s*vôi\s*hóa",
            r"đám\s*vôi\s*hóa",
            r"vôi\s*hóa\s*rải\s*rác\s*thùy",
            r"nốt\s*cản\s*quang",
            r"nốt\s*tăng\s*đậm\s*độ",
            r"vài\s*nốt",
            r"ổ\s*cặn\s*vôi\s*hóa",
        ],
    ),
    (
        "Màng phổi và vòm hoành",
        "Tù góc sườn hoành",
        [
            r"tù\s*(?:nhẹ\s*)?góc\s*sườn\s*hoành",
            r"góc\s*sườn\s*hoành.*(?:tù|mờ|cao)",
            r"mờ\s*(?:ngoại\s*vi\s*và\s*)?góc\s*sườn\s*hoành",
        ],
    ),
    (
        "Màng phổi và vòm hoành",
        "Tràn dịch màng phổi",
        [
            r"dịch\s*màng\s*phổi",
            r"tràn\s*dịch",
            r"mức\s*dịch",
        ],
    ),
    (
        "Màng phổi và vòm hoành",
        "Dày dính màng phổi và tràn khí màng phổi",
        [
            r"dày\s*màng\s*phổi",
            r"dính\s*màng\s*phổi",
            r"dày\s*dính",
            r"vôi\s*hóa\s*(?:dày\s*)?màng\s*phổi",
            r"tràn\s*khí",
            r"khí\s*màng\s*phổi",
            r"khí\s*dưới\s*da",
        ],
    ),
    (
        "Màng phổi và vòm hoành",
        "Bất thường vòm hoành",
        [
            r"vòm\s*hoành.*(?:lên\s*cao|đẩy\s*lên\s*cao|cao|thấp|dẹt|không\s*đều|nhão|thoát\s*vị|mờ|kém\s*rõ)",
            r"bất\s*thường\s*bờ\s*vòm\s*hoành",
            r"nhão\s*hoành",
            r"thoát\s*vị\s*hoành",
            r"liềm\s*hơi\s*dưới\s*hoành",
        ],
    ),
    (
        "Xương và thành ngực",
        "Vật liệu can thiệp và thiết bị y tế",
        [
            r"chỉ\s*thép",
            r"nẹp",
            r"vít",
            r"van\s*tim",
            r"máy\s*tạo\s*nhịp",
            r"sonde",
            r"ống\s*nội\s*khí\s*quản",
            r"catheter",
            r"kim\s*khí",
            r"dẫn\s*lưu",
        ],
    ),
    (
        "Nhu mô phổi",
        "Khối choán chỗ và bất thường trung thất",
        [
            r"\bu\b",
            r"khối\s*mờ",
            r"khối\s*choán\s*chỗ",
            r"khối\s*1/2",
            r"trung\s*thất\s*(?:rộng|to|lệch)",
            r"rộng\s*cung\s*trên\s*trung\s*thất",
            r"hạch",
            r"bướu\s*giáp",
            r"thứ\s*phát",
        ],
    ),
]


def is_strict_negated_or_normal(clause_text: str) -> bool:
    """Filter out normal, negated, and technically limited clauses while preserving positive qualifiers."""
    sp_low = str(clause_text).lower().strip()
    if not sp_low:
        return True

    s_temp = re.sub(
        r"không\s*(?:không\s*)?đồng\s*nhất|không\s*đ[ềê]u|mất\s*cân\s*đối|không\s*điển\s*hình|không\s*đặc\s*hiệu",
        " ",
        sp_low,
    )

    if re.search(
        r"\b(?:không\s*thấy|chưa\s*thấy|không\s*có|không\s*phát\s*hiện|không\s*ghi\s*nhận|"
        r"không\s*to|không\s*rộng|không\s*lệch|không\s*hẹp|chưa\s*loại\s*trừ|không\s*loại\s*trừ|"
        r"hạn\s*chế\s*đánh\s*giá|hít\s*không\s*đủ\s*sâu|trong\s*giới\s*hạn\s*(?:sinh\s*lý|bình\s*thường)|"
        r"bình\s*thường|cân\s*đối|sáng\s*đều|không\s*thay\s*đổi)\b",
        s_temp,
    ):
        return True

    if re.search(
        r"bờ\s*vòm\s*hoành\s*(?:hai\s*bên\s*)?đều|góc\s*sườn\s*hoành\s*(?:hai\s*bên\s*)?(?:nhọn|sáng)|"
        r"tù\s*góc\s*sườn\s*hoành\s*nhọn|phổi\s*hai\s*bên\s*sáng$",
        sp_low,
    ):
        return True

    return False


def preprocess_impression_for_pathology(text: str) -> str:
    """Clean and filter report impression text into positive pathology clauses."""
    if pd.isna(text):
        return ""
    cleaned_clauses = []
    for raw_line in str(text).split("\n"):
        line = re.sub(r"^[\-\+\*\s]+", "", raw_line.strip())
        line = re.sub(r"\.$", "", line).strip()
        if not line:
            continue

        line = re.sub(r"vôi\s*hóa\s*đày\s*màng\s*phổi", "vôi hóa dày màng phổi", line, flags=re.I)
        line = re.sub(r"vôi\s*hoá", "vôi hóa", line, flags=re.I)
        line = re.sub(r"góc\s*sường\s*hoành", "góc sườn hoành", line, flags=re.I)
        line = re.sub(r"dải\s*mơ\s*xơ", "dải mờ xơ", line, flags=re.I)
        line = re.sub(r"không\s*đêu", "không đều", line, flags=re.I)

        line = re.sub(r"\(?chưa\s*loại\s*trừ[^\n\.,;]*\)?", " ", line, flags=re.I)
        line = re.sub(r"\(?không\s*loại\s*trừ[^\n\.,;]*\)?", " ", line, flags=re.I)
        line = re.sub(
            r"(?:hiện\s*tại\s*)?(?:không|chưa)\s*(?:thấy|có|phát\s*hiện|ghi\s*nhận)[^\n\.,;]*",
            " ",
            line,
            flags=re.I,
        )
        line = re.sub(r"không\s*thay\s*đổi\s*so\s*với\s*phim\s*chụp\s*trước[^\n\.,;]*", " ", line, flags=re.I)

        for sub_clause in re.split(r"[;,\.]\s*", line):
            sc = re.sub(r"\s+", " ", sub_clause).strip()
            if len(sc) < 3 or is_strict_negated_or_normal(sc):
                continue
            cleaned_clauses.append(sc.lower())

    return " ; ".join(cleaned_clauses)


@st.cache_data(show_spinner=False)
def extract_pathology_matrix_from_series(impressions: pd.Series) -> pd.DataFrame:
    """Extract binary indicator matrix for all 13 disease groups with caching."""
    clean_series = impressions.apply(preprocess_impression_for_pathology)
    label_df = pd.DataFrame(index=impressions.index)

    for _, disease_name, kw_list in HIERARCHICAL_TAXONOMY:
        pattern = "|".join(kw_list)
        s_search = clean_series
        if disease_name == "Xơ hóa và dải xơ hoặc xẹp phổi":
            s_search = s_search.str.replace(r"xẹp[^;]*đốt\s*sống", "", regex=True, flags=re.I)
        label_df[disease_name] = s_search.str.contains(pattern, case=False, na=False, regex=True).astype(int)

    return label_df


def get_pathology_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Retrieve or compute multi-label binary indicators aligned to input dataframe."""
    if df.empty or "impressions" not in df.columns:
        return pd.DataFrame()
    return extract_pathology_matrix_from_series(df["impressions"])


@st.cache_data(show_spinner=False)
def compute_pathology_statistics(df: pd.DataFrame, label_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-disease prevalence, gender rates, and mean age."""
    if df.empty or label_df.empty:
        return pd.DataFrame()

    n_total = len(df)
    total_occurrences = int(label_df.sum().sum())
    disease_to_system = {disease: sys_name for sys_name, disease, _ in HIERARCHICAL_TAXONOMY}

    ages = pd.to_numeric(df.get("age", pd.Series(dtype=float)), errors="coerce")
    is_male = df.get("sex", pd.Series(dtype=str)) == "Nam"
    is_female = df.get("sex", pd.Series(dtype=str)) == "Nữ"
    male_count = is_male.sum()
    female_count = is_female.sum()

    stats_rows = []
    for col in label_df.columns:
        count = int(label_df[col].sum())
        p_disease = (count / n_total) * 100.0 if n_total > 0 else 0.0
        share_label = (count / total_occurrences) * 100.0 if total_occurrences > 0 else 0.0

        p_male = (label_df.loc[is_male, col].sum() / male_count * 100.0) if male_count > 0 else 0.0
        p_female = (label_df.loc[is_female, col].sum() / female_count * 100.0) if female_count > 0 else 0.0

        has_disease = label_df[col] == 1
        mean_age = ages[has_disease].mean() if has_disease.any() else np.nan

        stats_rows.append({
            "Hệ cơ quan": disease_to_system.get(col, "Khác"),
            "Nhóm bất thường": col,
            "Tên gọn": SHORT_LABEL_MAP.get(col, col),
            "Số ca": count,
            "Tỷ lệ P(Bệnh) (%)": round(p_disease, 2),
            "Tỷ trọng nhãn (%)": round(share_label, 2),
            "P(Bệnh | Nam) (%)": round(p_male, 2),
            "P(Bệnh | Nữ) (%)": round(p_female, 2),
            "Tuổi TB": round(mean_age, 1) if not np.isnan(mean_age) else 0.0,
        })

    return pd.DataFrame(stats_rows).sort_values(by="Số ca", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def compute_cooccurrence_pairs(
    label_df: pd.DataFrame,
    total_cases: int,
    top_cols_n: int = 10,
) -> pd.DataFrame:
    """Compute co-occurrence counts and percentage across top prevalent diseases."""
    if label_df.empty or total_cases <= 0:
        return pd.DataFrame()

    top_cols = label_df.sum().sort_values(ascending=False).head(top_cols_n).index.tolist()
    pair_rows = []

    for c1, c2 in combinations(top_cols, 2):
        both = int(((label_df[c1] == 1) & (label_df[c2] == 1)).sum())
        if both > 0:
            p_joint = (both / total_cases) * 100.0
            lbl1 = SHORT_LABEL_MAP.get(c1, c1)
            lbl2 = SHORT_LABEL_MAP.get(c2, c2)
            pair_rows.append({
                "Cặp bệnh lý đồng mắc": f"{lbl1} + {lbl2}",
                "Số ca đồng mắc": both,
                "Xác suất đồng mắc (%)": round(p_joint, 2),
            })

    return pd.DataFrame(pair_rows).sort_values(by="Số ca đồng mắc", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def compute_age_group_trends(df: pd.DataFrame, label_df: pd.DataFrame) -> dict[str, Any]:
    """Calculate rate of 5 common pathologies by age groups."""
    if df.empty or label_df.empty or "age" not in df.columns:
        return {}

    ages = pd.to_numeric(df["age"], errors="coerce")
    age_groups = pd.cut(
        ages,
        bins=[-1, 49, 64, 74, 150],
        labels=["< 50 tuổi", "50–64 tuổi", "65–74 tuổi", "≥ 75 tuổi"],
    )

    age_labels = ["< 50 tuổi", "50–64 tuổi", "65–74 tuổi", "≥ 75 tuổi"]
    series_data = []

    for full_name, short_name, color, marker in TOP5_AGE_TREND_DISEASES:
        rates = []
        for ag in age_labels:
            mask = age_groups == ag
            if mask.any() and full_name in label_df.columns:
                rate = float(label_df.loc[mask, full_name].mean() * 100.0)
            else:
                rate = 0.0
            rates.append(round(rate, 1))

        series_data.append({
            "full_name": full_name,
            "short_name": short_name,
            "color": color,
            "marker": marker,
            "rates": rates,
        })

    return {
        "age_labels": age_labels,
        "series": series_data,
    }


@st.cache_data(show_spinner=False)
def compute_comorbidity_distribution(label_df: pd.DataFrame) -> list[tuple[str, int, str, float]]:
    """Compute distribution of number of diseases found per chest X-ray image."""
    if label_df.empty:
        return []

    num_diseases = label_df.sum(axis=1)
    n_total = len(label_df)

    categories = [
        ("1 bệnh lý", int((num_diseases == 1).sum()), "#0D9488"),
        ("2 bệnh lý", int((num_diseases == 2).sum()), "#1E3A8A"),
        ("3 bệnh lý", int((num_diseases == 3).sum()), "#2563EB"),
        ("≥ 4 bệnh lý", int((num_diseases >= 4).sum()), "#D97706"),
        ("0 bệnh (bình thường)", int((num_diseases == 0).sum()), "#64748B"),
    ]

    result = []
    for name, count, color in categories:
        pct = (count / n_total) * 100.0 if n_total > 0 else 0.0
        result.append((name, count, color, round(pct, 1)))

    return result
