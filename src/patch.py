"""Streamlit 1.35+ backward compatibility patch for streamlit-drawable-canvas."""
from __future__ import annotations

import streamlit.elements.image as st_image

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
