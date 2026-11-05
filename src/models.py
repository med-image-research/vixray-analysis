from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import pandas as pd


@dataclass(frozen=True)
class DatasetBundle:
    master: pd.DataFrame
    annotations: pd.DataFrame


@dataclass(frozen=True)
class FilterSelection:
    splits: tuple[str, ...] = ("train", "val", "test")
    sexes: tuple[str, ...] = ()
    views: tuple[str, ...] = ()


FilterState = FilterSelection


@dataclass(frozen=True)
class FilteredBundle:
    master: pd.DataFrame
    annotations: pd.DataFrame


@dataclass
class MasterRecord:
    image_id: str
    split: str
    source_file: str
    row_index: int
    findings: str
    impressions: str
    age: str = ""
    sex: str = ""
    view: str = ""
    note: str = ""
    technique: str = ""
    image_width: int = 0
    image_height: int = 0
    image_url: str = ""
    drive_file_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "split": self.split,
            "source_file": self.source_file,
            "row_index": self.row_index,
            "findings": self.findings,
            "impressions": self.impressions,
            "age": self.age,
            "sex": self.sex,
            "view": self.view,
            "note": self.note,
            "technique": self.technique,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "image_url": self.image_url,
            "drive_file_id": self.drive_file_id,
        }


@dataclass
class ReferenceFindingRecord:
    reference_finding_id: str
    image_id: str
    image_url: str = ""
    finding_text: str = ""
    status: str = "Pending"
    boxes: list[list[float]] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_finding_id": self.reference_finding_id,
            "image_id": self.image_id,
            "image_url": self.image_url,
            "finding_text": self.finding_text,
            "status": self.status,
            "boxes": str(self.boxes),
            "updated_at": self.updated_at,
        }
