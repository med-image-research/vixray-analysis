"""Streamlit backward compatibility and canvas rendering patch."""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path
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


# 2. Patch frontend JS bundle of streamlit-drawable-canvas
# The React bundle executes `e.src = n + h` where `n = origin` from `?streamlitUrl=...`.
# On Streamlit Cloud deployments, `n` is `https://<subdomain>.streamlit.app`.
# If `h` is a Base64 data URL (`data:image/...`), `n + h` creates `https://<domain>data:image/...`
# which fails to load, leaving the canvas background completely blank.
# We patch `e.src=n+h` to `e.src=(h&&(h.indexOf("data:")===0||h.indexOf("http")===0))?h:n+h`.
def _patch_drawable_canvas_js() -> None:
    try:
        import streamlit_drawable_canvas as sdc

        build_dir = Path(sdc.__file__).resolve().parent / "frontend" / "build"
        if not build_dir.exists():
            return

        js_dir = build_dir / "static" / "js"
        if js_dir.exists():
            target = "e.src=n+h"
            replacement = 'e.src=(h&&(h.indexOf("data:")===0||h.indexOf("http")===0))?h:n+h'
            for js_file in js_dir.glob("main.*.chunk.js"):
                if "fixed" in js_file.name:
                    continue
                content = js_file.read_text(encoding="utf-8")
                if target in content:
                    patched = content.replace(target, replacement)
                    js_file.write_text(patched, encoding="utf-8")
                    fixed_file = js_dir / "main.fixed.chunk.js"
                    fixed_file.write_text(patched, encoding="utf-8")

        index_file = build_dir / "index.html"
        if index_file.exists():
            html = index_file.read_text(encoding="utf-8")
            new_html = re.sub(
                r'src="\./static/js/main\.[0-9a-f]+\.chunk\.js"',
                'src="./static/js/main.fixed.chunk.js"',
                html,
            )
            if new_html != html:
                index_file.write_text(new_html, encoding="utf-8")
    except Exception:
        pass


_patch_drawable_canvas_js()


# 3. Patch streamlit_drawable_canvas.st_canvas to reliably encode background_image to Base64
try:
    import streamlit_drawable_canvas as sdc
    from PIL import Image

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
