from __future__ import annotations

import io
import re
from typing import Any
import urllib.request

import pandas as pd
from PIL import Image
import streamlit as st

from src.config import ROOT_DIR
from src.models import DatasetBundle
from src.storage import GoogleSheetsStore


def load_data(store: GoogleSheetsStore) -> DatasetBundle:
    """Load both master and annotation datasets into a unified DatasetBundle.
    
    Master dataset uses fast local parquet caching.
    Annotations are always loaded fresh to guarantee real-time UI synchronization.
    """
    master = store.get_master()
    annotations = store.get_annotations()
    return DatasetBundle(master=master, annotations=annotations)


def extract_drive_id(url_or_id: Any) -> str:
    """Extract Google Drive file ID from a URL or raw ID string."""
    if not url_or_id:
        return ""
    text = str(url_or_id).strip()
    if "/" not in text and "=" not in text and len(text) > 15:
        return text
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", text)
    if m:
        return m.group(1)
    m = re.search(r"id=([a-zA-Z0-9_-]+)", text)
    if m:
        return m.group(1)
    return text


@st.cache_data(show_spinner=False, max_entries=300)
def fetch_image_from_drive(file_id: str) -> Image.Image | None:
    """Fetch and decode an image from Google Drive via fast Edge CDN or authenticated Drive API."""
    if not file_id:
        return None

    # 1. Fast Google Global Edge CDN (lh3.googleusercontent.com)
    for cdn_url in (
        f"https://lh3.googleusercontent.com/d/{file_id}=s1600",
        f"https://drive.google.com/thumbnail?id={file_id}&sz=w1600",
    ):
        try:
            req = urllib.request.Request(cdn_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                img_data = response.read()
                if len(img_data) > 5000:
                    image = Image.open(io.BytesIO(img_data)).convert("RGB")
                    image.load()
                    return image
        except Exception:
            continue

    # 2. Authenticated Google Drive API via Service Account (Fallback for private files)
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            from google.oauth2.service_account import Credentials
            from google.auth.transport.requests import Request

            gcp_conf = dict(st.secrets["gcp_service_account"])
            scopes = ["https://www.googleapis.com/auth/drive.readonly"]
            creds = Credentials.from_service_account_info(gcp_conf, scopes=scopes)
            creds.refresh(Request())

            api_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            req = urllib.request.Request(
                api_url,
                headers={"Authorization": f"Bearer {creds.token}"},
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                img_data = response.read()
                image = Image.open(io.BytesIO(img_data)).convert("RGB")
                image.load()
                return image
    except Exception:
        pass

    return None


def get_case_image(case_row: pd.Series | dict[str, Any]) -> Image.Image | None:
    """Retrieve image for a case: Google Drive first, then local files fallback."""
    # 1. Try Google Drive (Primary source for Cloud deployment)
    drive_id = str(case_row.get("drive_file_id", "")).strip()
    if not drive_id:
        drive_id = extract_drive_id(case_row.get("image_url", ""))

    if drive_id:
        drive_img = fetch_image_from_drive(drive_id)
        if drive_img is not None:
            return drive_img

    # 2. Try local disk images/ folder (e.g. VX-000001.jpg)
    image_id = str(case_row.get("image_id", "")).strip()
    if image_id:
        local_path = ROOT_DIR / "images" / f"{image_id}.jpg"
        if local_path.exists():
            try:
                img = Image.open(local_path).convert("RGB")
                img.load()
                return img
            except Exception:
                pass

    return None


@st.cache_data(show_spinner=False, max_entries=50)
def get_cached_canvas_bg(image_id: str, _img: Image.Image, width: int, height: int) -> Image.Image:
    """Pre-downsample canvas background image to avoid CPU lag during drawing."""
    return _img.resize((width, height), Image.Resampling.BILINEAR)
