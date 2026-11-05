from __future__ import annotations

import ast
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

CLINICAL_PALETTE = [
    "#FF0000",
    "#FFD600",
    "#0080FF",
    "#00C853",
]


def parse_boxes(value: object) -> list[tuple[float, float, float, float]]:
    """Parse bounding boxes stored as string representation of list or raw list."""
    if value is None or (isinstance(value, float) and value != value):
        return []

    if isinstance(value, (list, tuple)):
        parsed = value
    else:
        raw_str = str(value).strip()
        if not raw_str or raw_str in ("[]", "()", '""'):
            return []
        try:
            parsed = ast.literal_eval(raw_str)
        except Exception:
            try:
                parsed = json.loads(raw_str)
            except Exception as exc:
                raise ValueError(f"Cannot parse boxes string: {value}") from exc

    if not isinstance(parsed, (list, tuple)):
        raise ValueError("boxes must be a list or tuple")

    result: list[tuple[float, float, float, float]] = []
    for box in parsed:
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            raise ValueError(f"Invalid bbox format: {box}")
        result.append(tuple(float(v) for v in box))
    return result


def _finding_key(row: object) -> str:
    if isinstance(row, dict):
        return str(row.get("reference_finding_id") or row.get("finding_id") or "unknown")
    for attr in ("reference_finding_id", "finding_id", "id"):
        val = getattr(row, attr, None)
        if val is not None:
            return str(val)
    return "unknown"


def _finding_color(index: int) -> str:
    return CLINICAL_PALETTE[index % len(CLINICAL_PALETTE)]


def finding_colors(rows: Iterable[object]) -> dict[str, str]:
    """Map each finding in the case to a high-contrast clinical color."""
    colors: dict[str, str] = {}
    for row in rows:
        key = _finding_key(row)
        if key not in colors:
            colors[key] = _finding_color(len(colors))
    return colors


def _get_font(size: int = 14) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font that fully supports Vietnamese Unicode characters."""
    # 1. Bundled DejaVuSans-Bold font in repo
    local_font = Path(__file__).resolve().parent / "fonts" / "DejaVuSans-Bold.ttf"
    if local_font.exists():
        try:
            return ImageFont.truetype(str(local_font), size)
        except Exception:
            pass

    # 2. Matplotlib fonts directory
    try:
        import matplotlib

        font_dir = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
        for name in ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
            p = font_dir / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    except Exception:
        pass

    # 3. Common system fonts
    for font_name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "tahoma.ttf", "segoeui.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue

    return ImageFont.load_default()


def draw_case(
    image: Image.Image,
    rows: Any,
    colors: Mapping[str, str] | None = None,
) -> Image.Image:
    """Render bounding boxes and clinical labels onto the image with full Unicode support."""
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    min_dim = min(canvas.size)
    stroke_width = max(3, round(min_dim * 0.003))
    font_size = max(14, round(min_dim * 0.018))
    font = _get_font(font_size)

    rows_list = list(rows.itertuples() if hasattr(rows, "itertuples") else rows)
    color_map = dict(colors or finding_colors(rows_list))

    for row in rows_list:
        key = _finding_key(row)
        color = color_map.get(key, "#FF0000")

        if isinstance(row, dict):
            raw_boxes = row.get("boxes") or row.get("bboxes")
            finding_text = row.get("finding_text") or ""
        else:
            raw_boxes = getattr(row, "boxes", None) or getattr(row, "bboxes", None)
            finding_text = getattr(row, "finding_text", None) or ""

        if not raw_boxes:
            continue

        try:
            boxes = parse_boxes(raw_boxes)
        except Exception:
            continue

        short_id = key.split("-")[-1]
        label = f"{short_id} - {finding_text}" if finding_text else short_id
        if len(label) > 40:
            label = label[:37] + "..."

        for x, y, width, height in boxes:
            x2, y2 = x + width, y + height
            draw.rectangle((x, y, x2, y2), outline=color, width=stroke_width)

            text_box = draw.textbbox((0, 0), label, font=font)
            tw = text_box[2] - text_box[0]
            th = text_box[3] - text_box[1]
            pad_x = max(3, round(font_size * 0.25))
            pad_y = max(2, round(font_size * 0.18))

            badge_h = th + pad_y * 2
            badge_w = tw + pad_x * 2

            if y - badge_h >= 0:
                badge_top = y - badge_h
                badge_bottom = y
            else:
                badge_top = y
                badge_bottom = y + badge_h

            badge_left = int(x)
            badge_right = int(x) + badge_w

            draw.rectangle((badge_left, badge_top, badge_right, badge_bottom), fill=color)
            draw.text((badge_left + pad_x, badge_top + pad_y), label, fill="white", font=font)

    return canvas


def scale_boxes_to_original(
    boxes: list[list[float]],
    scale_x: float,
    scale_y: float,
) -> list[list[int]]:
    """Scale canvas pixel coordinates back to original image dimensions [x, y, w, h]."""
    if scale_x <= 0 or scale_y <= 0:
        return []
    result: list[list[int]] = []
    for box in boxes:
        if len(box) != 4:
            continue
        x, y, width, height = box
        result.append([
            max(0, round(x / scale_x)),
            max(0, round(y / scale_y)),
            max(1, round(width / scale_x)),
            max(1, round(height / scale_y)),
        ])
    return result


def extract_canvas_boxes(
    canvas_objects: list[dict[str, Any]],
    scale_x: float,
    scale_y: float,
) -> list[list[int]]:
    """Extract rectangle bounding boxes from streamlit-drawable-canvas fabric.js output."""
    boxes: list[list[float]] = []
    for obj in canvas_objects:
        if obj.get("type") != "rect":
            continue
        left = float(obj.get("left", 0))
        top = float(obj.get("top", 0))
        width = float(obj.get("width", 0)) * float(obj.get("scaleX", 1))
        height = float(obj.get("height", 0)) * float(obj.get("scaleY", 1))
        boxes.append([left, top, width, height])
    return scale_boxes_to_original(boxes, scale_x, scale_y)
