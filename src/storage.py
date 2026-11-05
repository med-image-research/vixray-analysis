from __future__ import annotations

import datetime
from pathlib import Path
import re
from typing import Any

import pandas as pd
import streamlit as st

from src.config import (
    ANNOTATION_COLUMNS,
    LOCAL_ANNOTATIONS_FILE,
    LOCAL_MASTER_FILE,
    MASTER_COLUMNS,
)

try:
    import gspread
    from google.oauth2.service_account import Credentials

    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_master_records(_sheet) -> list[dict[str, Any]]:
    return _sheet.get_all_records()


@st.cache_data(show_spinner=False)
def _read_local_master_file(file_path: Path) -> pd.DataFrame:
    return pd.read_parquet(file_path)


@st.cache_data(ttl=15, show_spinner=False)
def _fetch_annotation_records(_sheet) -> list[dict[str, Any]]:
    return _sheet.get_all_records()


class GoogleSheetsStore:
    """Storage backend supporting Google Sheets with automatic local fallback."""

    def __init__(self) -> None:
        self.is_sheets_connected = False
        self.master_sheet = None
        self.annotation_sheet = None
        self.backend_type = "local"
        self._cached_annotations: pd.DataFrame | None = None
        self._init_backend()

    def _init_backend(self) -> None:
        if not GSPREAD_AVAILABLE:
            self.backend_type = "local"
            return

        try:
            if "google_sheets" not in st.secrets or "gcp_service_account" not in st.secrets:
                self.backend_type = "local"
                return

            sheets_conf = st.secrets["google_sheets"]
            gcp_conf = st.secrets["gcp_service_account"]

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_info(dict(gcp_conf), scopes=scopes)
            client = gspread.authorize(creds)

            master_id = sheets_conf.get("master_sheet_id")
            annot_id = sheets_conf.get("annotation_sheet_id")

            if master_id and annot_id:
                master_doc = client.open_by_key(master_id)
                self.master_sheet = master_doc.get_worksheet(0)

                annot_doc = client.open_by_key(annot_id)
                self.annotation_sheet = annot_doc.get_worksheet(0)

                self.is_sheets_connected = True
                self.backend_type = "sheets"
        except Exception:
            self.backend_type = "local"
            self.is_sheets_connected = False

    def get_master(self, force_refresh: bool = False) -> pd.DataFrame:
        """Fetch master cases records (loads local parquet snapshot by default)."""
        if not force_refresh and LOCAL_MASTER_FILE.exists():
            try:
                df = _read_local_master_file(LOCAL_MASTER_FILE)
                if len(df) >= 5400 and "image_url" in df.columns:
                    return df
            except Exception:
                pass

        if self.is_sheets_connected and self.master_sheet is not None:
            try:
                records = _fetch_master_records(self.master_sheet)
                df = pd.DataFrame(records)
                for col in MASTER_COLUMNS:
                    if col not in df.columns:
                        df[col] = ""
                try:
                    LOCAL_MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)
                    df.to_parquet(LOCAL_MASTER_FILE, index=False)
                except Exception:
                    pass
                return df
            except Exception as exc:
                st.warning(f"Không thể tải Master từ Google Sheets ({exc}), dùng dữ liệu cục bộ.")

        if LOCAL_MASTER_FILE.exists():
            try:
                return pd.read_parquet(LOCAL_MASTER_FILE)
            except Exception:
                pass

        return pd.DataFrame(columns=MASTER_COLUMNS)

    def save_master(self, df: pd.DataFrame) -> bool:
        """Save master records locally and synchronize with Google Sheets."""
        LOCAL_MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(LOCAL_MASTER_FILE, index=False)

        if self.is_sheets_connected and self.master_sheet is not None:
            try:
                cleaned_df = df.copy().fillna("")
                cols = [c for c in MASTER_COLUMNS if c in cleaned_df.columns]
                values = [cols] + cleaned_df[cols].astype(str).values.tolist()
                self.master_sheet.clear()
                self.master_sheet.update(range_name="A1", values=values)
                _fetch_master_records.clear()
                return True
            except Exception as exc:
                st.error(f"Lỗi khi đồng bộ Master lên Google Sheets: {exc}")
                return False
        return True

    def get_annotations(self, force_refresh: bool = False) -> pd.DataFrame:
        """Fetch all Reference Findings annotations with in-memory caching."""
        if not force_refresh and self._cached_annotations is not None:
            return self._cached_annotations.copy()

        if force_refresh:
            self._cached_annotations = None
            _fetch_annotation_records.clear()

        if self.is_sheets_connected and self.annotation_sheet is not None:
            try:
                records = _fetch_annotation_records(self.annotation_sheet)
                df = pd.DataFrame(records)
                for col in ANNOTATION_COLUMNS:
                    if col not in df.columns:
                        df[col] = ""
                try:
                    LOCAL_ANNOTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
                    df[ANNOTATION_COLUMNS].to_csv(LOCAL_ANNOTATIONS_FILE, index=False)
                except Exception:
                    pass
                self._cached_annotations = df[ANNOTATION_COLUMNS].copy()
                return self._cached_annotations.copy()
            except Exception as exc:
                st.warning(f"Không thể nạp gán nhãn từ Google Sheets ({exc}), dùng bản lưu cục bộ.")

        if LOCAL_ANNOTATIONS_FILE.exists():
            try:
                df = pd.read_csv(LOCAL_ANNOTATIONS_FILE, dtype=str)
                for col in ANNOTATION_COLUMNS:
                    if col not in df.columns:
                        df[col] = ""
                self._cached_annotations = df[ANNOTATION_COLUMNS].copy()
                return self._cached_annotations.copy()
            except Exception:
                pass

        empty_df = pd.DataFrame(columns=ANNOTATION_COLUMNS)
        self._cached_annotations = empty_df.copy()
        return empty_df

    def save_annotation(self, record: dict[str, Any]) -> bool:
        """Create or update a Reference Finding annotation."""
        df = self.get_annotations()
        ref_id = str(record.get("reference_finding_id", "")).strip()
        if not ref_id:
            return False

        record["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(record.get("boxes"), (list, tuple)):
            record["boxes"] = str(record["boxes"])

        if not df.empty and ref_id in df["reference_finding_id"].astype(str).values:
            idx = df[df["reference_finding_id"].astype(str) == ref_id].index[0]
            for col in ANNOTATION_COLUMNS:
                if col in record:
                    df.at[idx, col] = record[col]
        else:
            new_row = {col: record.get(col, "") for col in ANNOTATION_COLUMNS}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        LOCAL_ANNOTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(LOCAL_ANNOTATIONS_FILE, index=False)
        self._cached_annotations = df[ANNOTATION_COLUMNS].copy()

        if self.is_sheets_connected and self.annotation_sheet is not None:
            try:
                cleaned_df = df.copy().fillna("")
                values = [ANNOTATION_COLUMNS] + cleaned_df[ANNOTATION_COLUMNS].astype(str).values.tolist()
                self.annotation_sheet.clear()
                self.annotation_sheet.update(range_name="A1", values=values)
                _fetch_annotation_records.clear()
                return True
            except Exception as exc:
                st.error(f"Lỗi khi đồng bộ gán nhãn lên Google Sheets: {exc}")
                return False

        return True

    def delete_annotation(self, reference_finding_id: str) -> bool:
        """Delete an annotation by its reference_finding_id."""
        df = self.get_annotations()
        if df.empty:
            return False

        mask = df["reference_finding_id"].astype(str) != str(reference_finding_id).strip()
        updated_df = df[mask].reset_index(drop=True)

        LOCAL_ANNOTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        updated_df.to_csv(LOCAL_ANNOTATIONS_FILE, index=False)
        self._cached_annotations = updated_df[ANNOTATION_COLUMNS].copy()

        if self.is_sheets_connected and self.annotation_sheet is not None:
            try:
                cleaned_df = updated_df.copy().fillna("")
                values = [ANNOTATION_COLUMNS] + cleaned_df[ANNOTATION_COLUMNS].astype(str).values.tolist()
                self.annotation_sheet.clear()
                self.annotation_sheet.update(range_name="A1", values=values)
                _fetch_annotation_records.clear()
                return True
            except Exception as exc:
                st.error(f"Lỗi khi xóa gán nhãn trên Google Sheets: {exc}")
                return False

        return True

    def get_next_reference_id(self, image_id: str = "") -> str:
        """Generate the next auto-incrementing Reference Finding ID: <image_id>-RF<k>."""
        if not image_id:
            df = self.get_annotations()
            return f"RF{len(df) + 1}"

        df = self.get_annotations()
        numbers: list[int] = []
        if not df.empty and "image_id" in df.columns and "reference_finding_id" in df.columns:
            case_subset = df[df["image_id"] == image_id]
            for val in case_subset["reference_finding_id"].dropna():
                text = str(val).strip()
                m = re.search(r"RF[-_]?(\d+)$", text, re.IGNORECASE)
                if m:
                    try:
                        numbers.append(int(m.group(1)))
                    except ValueError:
                        pass
                else:
                    m2 = re.search(r"(\d+)$", text)
                    if m2:
                        try:
                            numbers.append(int(m2.group(1)))
                        except ValueError:
                            pass
        next_num = max(numbers, default=0) + 1
        return f"{image_id}-RF{next_num}"
