"""Streamlit backward compatibility and canvas rendering patch."""
from __future__ import annotations

import base64
import io
from pathlib import Path
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import streamlit.elements.image as st_image
from PIL import Image

# 1. Compatibility for st_image.image_to_url if missing in Streamlit >= 1.40
if not hasattr(st_image, "image_to_url"):
    try:
        from streamlit.elements.lib.image_utils import image_to_url as _new_image_to_url
        from streamlit.elements.lib.layout_utils import LayoutConfig

        def _compat_image_to_url(image, width, clamp, channels, output_format, image_id):
            layout = LayoutConfig(width=width) if width is not None else LayoutConfig()
            return _new_image_to_url(image, layout, clamp, channels, output_format, image_id)

        st_image.image_to_url = _compat_image_to_url
    except Exception:
        pass


# 2. Self-contained Custom Component for Canvas
# We bundle the patched React frontend directly inside `src/canvas_frontend`.
# This completely eliminates issues on Streamlit Cloud where:
# - site-packages may be read-only or impossible to monkey-patch at runtime
# - CDNs or reverse proxies prepend origin domain to Base64 data URLs (e.g. https://...data:image/...)
# - image_to_url / MediaFileManager paths fail or throw 404s
FRONTEND_DIR = Path(__file__).resolve().parent / "canvas_frontend"
_custom_canvas_func = components.declare_component("vixray_canvas", path=str(FRONTEND_DIR))

try:
    import streamlit_drawable_canvas as sdc

    def _robust_st_canvas(
        fill_color: str = "#eee",
        stroke_width: int = 20,
        stroke_color: str = "black",
        background_color: str = "",
        background_image: Image.Image | str | None = None,
        update_streamlit: bool = True,
        height: int = 400,
        width: int = 600,
        drawing_mode: str = "freedraw",
        initial_drawing: dict | None = None,
        display_toolbar: bool = True,
        point_display_radius: int = 3,
        key: str | None = None,
    ):
        background_image_url = None
        if background_image is not None:
            if isinstance(background_image, str):
                background_image_url = background_image
            else:
                resized_img = sdc._resize_img(background_image, height, width)
                buf = io.BytesIO()
                resized_img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                background_image_url = f"data:image/png;base64,{b64}"
            background_color = ""

        if initial_drawing is None:
            initial_drawing = {"version": "4.4.0"}
        else:
            initial_drawing = dict(initial_drawing)
        initial_drawing["background"] = background_color

        component_value = _custom_canvas_func(
            fillColor=fill_color,
            strokeWidth=stroke_width,
            strokeColor=stroke_color,
            backgroundColor=background_color,
            backgroundImageURL=background_image_url,
            realtimeUpdateStreamlit=update_streamlit and (drawing_mode != "polygon"),
            canvasHeight=height,
            canvasWidth=width,
            drawingMode=drawing_mode,
            initialDrawing=initial_drawing,
            displayToolbar=display_toolbar,
            displayRadius=point_display_radius,
            key=key,
            default=None,
        )
        if component_value is None:
            return sdc.CanvasResult(None, None)

        raw_val = component_value.get("raw") if isinstance(component_value, dict) else None
        return sdc.CanvasResult(
            None,
            raw_val,
        )

    # Patch both sdc.st_canvas and export it directly
    sdc.st_canvas = _robust_st_canvas
    sdc._component_func = _custom_canvas_func
    st_canvas = _robust_st_canvas

except Exception:
    st_canvas = None
