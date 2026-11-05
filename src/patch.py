"""Streamlit backward compatibility and canvas rendering patch."""
from __future__ import annotations

import base64
import io
import numpy as np
import streamlit as st
import streamlit.elements.image as st_image

# 1. Compatibility for st_image.image_to_url if missing
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

# 2. Patch streamlit_drawable_canvas to use base64 data URLs for background image
# This prevents broken/missing images on cloud deployments (Streamlit Cloud, CORS, relative /media/ URLs)
try:
    import streamlit_drawable_canvas as sdc
    from PIL import Image

    def _robust_st_canvas(
        fill_color: str = "#eee",
        stroke_width: int = 20,
        stroke_color: str = "black",
        background_color: str = "",
        background_image: Image.Image | None = None,
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
        if background_image:
            resized_img = sdc._resize_img(background_image, height, width)
            buf = io.BytesIO()
            resized_img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            background_image_url = f"data:image/png;base64,{b64}"
            background_color = ""

        initial_drawing = (
            {"version": "4.4.0"} if initial_drawing is None else initial_drawing
        )
        initial_drawing["background"] = background_color

        component_value = sdc._component_func(
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
            return sdc.CanvasResult

        return sdc.CanvasResult(
            np.asarray(sdc._data_url_to_image(component_value["data"])),
            component_value["raw"],
        )

    sdc.st_canvas = _robust_st_canvas
except Exception:
    pass
