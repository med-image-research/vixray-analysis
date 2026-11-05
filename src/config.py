from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "storage"
LOCAL_MASTER_FILE = DATA_DIR / "master.parquet"
LOCAL_ANNOTATIONS_FILE = DATA_DIR / "annotations.csv"

MASTER_COLUMNS: list[str] = [
    "image_id",
    "split",
    "source_file",
    "row_index",
    "findings",
    "impressions",
    "age",
    "sex",
    "view",
    "note",
    "technique",
    "image_width",
    "image_height",
    "image_url",
    "drive_file_id",
]

ANNOTATION_COLUMNS: list[str] = [
    "reference_finding_id",
    "image_id",
    "image_url",
    "finding_text",
    "status",
    "boxes",
    "updated_at",
]

STATUS_CHOICES: list[str] = [
    "Pending",
    "Annotated",
    "Reviewed",
    "Not suitable",
]

STATUS_DISPLAY_MAP: dict[str, str] = {
    "Pending": "Chưa annotate",
    "Annotated": "Đã annotate",
    "Reviewed": "Đã kiểm duyệt",
    "Not suitable": "Không phù hợp",
}

STATUS_REVERSE_MAP: dict[str, str] = {v: k for k, v in STATUS_DISPLAY_MAP.items()}

SPLIT_CHOICES: list[str] = [
    "train",
    "val",
    "test",
]

IMAGE_ID_PREFIX = "VX-"
REFERENCE_FINDING_ID_PREFIX = "RF-"
