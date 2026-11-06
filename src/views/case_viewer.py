from __future__ import annotations

import base64
import io
from typing import Any
import pandas as pd
import streamlit as st
from PIL import Image

from src.bbox import (
    draw_case,
    extract_canvas_boxes,
    finding_colors,
    parse_boxes,
)
from src.config import STATUS_CHOICES, STATUS_DISPLAY_MAP
from src.data import extract_drive_id, get_cached_canvas_bg, get_case_image
from src.models import DatasetBundle, FilteredBundle
from src.storage import GoogleSheetsStore

try:
    from src.patch import st_canvas

    CANVAS_AVAILABLE = st_canvas is not None
except Exception:
    try:
        from streamlit_drawable_canvas import st_canvas

        CANVAS_AVAILABLE = True
    except ImportError:
        CANVAS_AVAILABLE = False


COLOR_MAP = {
    "Đỏ": ("#FF0000", "rgba(255, 0, 0, 0.15)"),
    "Vàng": ("#FFD600", "rgba(255, 214, 0, 0.15)"),
    "Xanh dương": ("#0080FF", "rgba(0, 128, 255, 0.15)"),
    "Xanh lá": ("#00C853", "rgba(0, 200, 83, 0.15)"),
}


def _clear_form_state() -> None:
    """Safely reset all annotation form fields and editing session state."""
    st.session_state.editing_rf_id = None
    for k in ("form_finding_text", "form_boxes", "edit_initial_boxes", "last_seen_boxes"):
        st.session_state.pop(k, None)
    st.session_state["form_status"] = "Pending"


def _make_initial_drawing(
    boxes: list[list[int] | tuple[float, float, float, float]],
    scale: float,
    stroke_color: str = "#FF0000",
    stroke_width: int = 1,
    fill_color: str = "rgba(255, 0, 0, 0.15)",
) -> dict[str, Any] | None:
    objects = []
    for box in boxes:
        if len(box) == 4:
            x, y, w, h = box
            objects.append({
                "type": "rect",
                "version": "4.4.0",
                "originX": "left",
                "originY": "top",
                "left": float(x * scale),
                "top": float(y * scale),
                "width": float(w * scale),
                "height": float(h * scale),
                "fill": fill_color,
                "stroke": stroke_color,
                "strokeWidth": stroke_width,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "visible": True,
            })
    return {"version": "4.4.0", "objects": objects} if objects else None


def _render_clickable_image(
    image: Image.Image,
    file_id: str,
    caption: str,
) -> None:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=92)
    b64 = base64.b64encode(buf.getvalue()).decode()
    data_url = f"data:image/jpeg;base64,{b64}"
    target_url = f"https://lh3.googleusercontent.com/d/{file_id}=s3000" if file_id else data_url

    html_code = (
        f'<div style="background:#0e0e0e; border-radius:6px; padding:6px; text-align:center;">'
        f'<a href="{target_url}" target="_blank" title="Bấm vào ảnh để phóng to toàn màn hình">'
        f'<img src="{data_url}" style="max-width:100%; height:auto; border-radius:4px; cursor:zoom-in;" />'
        f'</a>'
        f'<div style="color:#94A3B8; font-size:0.82rem; margin-top:6px;">'
        f'{caption} &middot; <span style="color:#38BDF8;">(Bấm vào ảnh để mở toàn màn hình)</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html_code, unsafe_allow_html=True)


def _render_navigation(case_ids: list[str]) -> str:
    col_prev, col_sel, col_next = st.columns([1, 4, 1])
    current_idx = st.session_state.get("current_case_idx", 0)
    if current_idx >= len(case_ids):
        current_idx = 0

    with col_prev:
        if st.button("Ca trước", use_container_width=True):
            st.session_state.current_case_idx = max(0, current_idx - 1)
            st.rerun()

    with col_next:
        if st.button("Ca tiếp theo", use_container_width=True):
            st.session_state.current_case_idx = min(len(case_ids) - 1, current_idx + 1)
            st.rerun()

    with col_sel:
        selected_id = st.selectbox(
            "Chọn Image ID",
            options=case_ids,
            index=current_idx,
            label_visibility="collapsed",
        )
        st.session_state.current_case_idx = case_ids.index(selected_id)

    return selected_id


def _render_kpi_summary(case_row: pd.Series, case_findings: pd.DataFrame) -> None:
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Tập dữ liệu", str(case_row.get("split", "N/A")))
    m2.metric("Hướng chụp", str(case_row.get("view", "PA")))
    m3.metric("Tuổi", str(case_row.get("age", "N/A")))
    m4.metric("Giới tính", str(case_row.get("sex", "N/A")))
    m5.metric("Số Reference Finding", len(case_findings))

    total_boxes = 0
    if not case_findings.empty and "boxes" in case_findings.columns:
        for b_raw in case_findings["boxes"]:
            try:
                total_boxes += len(parse_boxes(b_raw))
            except Exception:
                pass
    m6.metric("Số bounding box", total_boxes)
    st.markdown("---")


def _render_image_view(
    img: Image.Image,
    selected_id: str,
    file_id: str,
    case_findings: pd.DataFrame,
    orig_w: int,
    orig_h: int,
) -> None:
    if not case_findings.empty:
        colors = finding_colors(case_findings.itertuples())
        annotated_image = draw_case(img, case_findings, colors)
        caption = f"{selected_id} · Kích thước gốc: {orig_w} × {orig_h}px"
        _render_clickable_image(annotated_image, file_id, caption)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        st.markdown("**Chú thích màu sắc:**")
        for row in case_findings.itertuples():
            ref_id = getattr(row, "reference_finding_id", "RF")
            color = colors.get(str(ref_id), "#888888")
            finding_text = getattr(row, "finding_text", "")
            status = getattr(row, "status", "Pending")
            status_vn = STATUS_DISPLAY_MAP.get(status, status)
            boxes_count = len(parse_boxes(getattr(row, "boxes", "")))
            st.markdown(
                f'<div style="margin-bottom: 4px;">'
                f'<span style="display:inline-block;width:12px;height:12px;background:{color};'
                f'border-radius:2px;margin-right:8px;vertical-align:middle;"></span>'
                f'<b>{ref_id}</b>: {finding_text} '
                f'<span class="status-badge status-{status.lower().replace(" ", "")}">{status_vn}</span> '
                f'<i>- {boxes_count} bounding box</i>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        caption = f"{selected_id} · Chưa có Reference Finding nào được lưu"
        _render_clickable_image(img, file_id, caption)


def _render_canvas_view(
    img: Image.Image,
    selected_id: str,
    is_editing: bool,
    orig_w: int,
    orig_h: int,
) -> list[list[int]]:
    if not CANVAS_AVAILABLE:
        st.error("Chưa tải được component Canvas.")
        return []

    st.caption("Dùng chuột kéo trên ảnh để vẽ bounding box. Sử dụng biểu tượng thùng rác bên dưới ảnh để xóa.")

    selected_color = st.radio(
        "Màu viền:",
        list(COLOR_MAP.keys()),
        horizontal=True,
        index=0,
        key="canvas_color_radio",
    )
    stroke_color, fill_color = COLOR_MAP[selected_color]
    stroke_width = 1
    drawing_mode = "rect"

    canvas_width = 580
    scale = canvas_width / orig_w
    canvas_height = round(orig_h * scale)

    initial_drawing = None
    if is_editing:
        raw_b = st.session_state.get("edit_initial_boxes", "")
        if raw_b:
            try:
                parsed_b = parse_boxes(raw_b)
                if parsed_b:
                    initial_drawing = _make_initial_drawing(
                        parsed_b, scale, stroke_color, stroke_width, fill_color
                    )
            except Exception:
                pass

    bg_img = get_cached_canvas_bg(selected_id, img, canvas_width, canvas_height)
    canvas_key = f"canvas_{selected_id}_{st.session_state.get('editing_rf_id', 'new')}_{canvas_width}"
    canvas_result = st_canvas(
        fill_color=fill_color,
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_image=bg_img,
        height=canvas_height,
        width=canvas_width,
        drawing_mode=drawing_mode,
        initial_drawing=initial_drawing,
        display_toolbar=True,
        key=canvas_key,
    )

    objects = canvas_result.json_data.get("objects", []) if canvas_result and canvas_result.json_data else []
    drawn_boxes = extract_canvas_boxes(objects, scale_x=scale, scale_y=scale)

    if is_editing and "last_seen_boxes" not in st.session_state:
        st.session_state["last_seen_boxes"] = parse_boxes(st.session_state.get("edit_initial_boxes", "[]"))

    last_seen_boxes = st.session_state.get("last_seen_boxes")
    if canvas_result and canvas_result.json_data is not None and last_seen_boxes != drawn_boxes:
        st.session_state["last_seen_boxes"] = drawn_boxes
        st.session_state["form_boxes"] = str(drawn_boxes)
        st.session_state["edit_initial_boxes"] = str(drawn_boxes)
        st.session_state["form_boxes_key_idx"] = st.session_state.get("form_boxes_key_idx", 0) + 1
        st.session_state["form_status"] = "Annotated" if drawn_boxes else "Pending"

    if drawn_boxes:
        st.success(f"Đã vẽ **{len(drawn_boxes)}** bounding box.")

    return drawn_boxes


def _render_clinical_context(selected_id: str, case_row: pd.Series) -> None:
    st.subheader("Ngữ cảnh lâm sàng")

    with st.container():
        st.markdown("**Mô tả hình ảnh:**")
        findings_text = str(case_row.get("findings", "")).strip()
        if findings_text:
            st.info(findings_text)
        else:
            st.caption("Không có mô tả hình ảnh.")

        st.markdown("**Kết luận chẩn đoán:**")
        impressions_text = str(case_row.get("impressions", "")).strip()
        if impressions_text:
            st.success(impressions_text)
        else:
            st.caption("Không có kết luận chẩn đoán.")

    with st.expander("Thông tin kỹ thuật ca chụp"):
        st.json({
            "Mã ảnh": selected_id,
            "File nguồn": str(case_row.get("source_file", "")),
            "Dòng gốc": int(case_row.get("row_index", 0)),
            "Kỹ thuật": str(case_row.get("technique", "")),
            "Ghi chú ca": str(case_row.get("note", "")),
            "Đường dẫn ảnh": str(case_row.get("image_url", "")),
        })

    st.markdown("---")


def _render_findings_list(case_findings: pd.DataFrame, store: GoogleSheetsStore) -> None:
    st.markdown(f"#### Reference Finding đã lưu ({len(case_findings)})")
    if not case_findings.empty:
        for _, r in case_findings.iterrows():
            rf_id = str(r.get("reference_finding_id", ""))
            f_txt = str(r.get("finding_text", ""))
            stt = str(r.get("status", "Pending"))
            stt_vn = STATUS_DISPLAY_MAP.get(stt, stt)
            boxes_val = str(r.get("boxes", "[]"))

            c_box1, c_box2, c_box3 = st.columns([3, 1, 1])
            with c_box1:
                st.markdown(
                    f"**{rf_id}**: {f_txt} "
                    f'<span class="status-badge status-{stt.lower().replace(" ", "")}">{stt_vn}</span>',
                    unsafe_allow_html=True,
                )
                st.caption(f"Tọa độ các khung: `{boxes_val}`")
            with c_box2:
                if st.button("Sửa", key=f"edit_{rf_id}", use_container_width=True):
                    st.session_state.editing_rf_id = rf_id
                    st.session_state["form_finding_text"] = f_txt
                    st.session_state["form_boxes"] = boxes_val
                    st.session_state["form_status"] = stt
                    st.session_state["edit_initial_boxes"] = boxes_val
                    st.session_state["last_seen_boxes"] = parse_boxes(boxes_val)
                    st.session_state["pending_mode_switch"] = "Chế độ vẽ bounding box"
                    st.rerun()
            with c_box3:
                if st.button("Xóa", key=f"del_{rf_id}", use_container_width=True):
                    store.delete_annotation(rf_id)
                    if st.session_state.get("editing_rf_id") == rf_id:
                        _clear_form_state()
                    st.rerun()
    else:
        st.info("Chưa có Reference Finding nào cho ca này.")


def _render_annotation_form(
    store: GoogleSheetsStore,
    selected_id: str,
    case_row: pd.Series,
    is_editing: bool,
) -> None:
    if not is_editing:
        st.markdown("---")
    current_rf_id = (
        st.session_state.editing_rf_id
        if is_editing
        else store.get_next_reference_id(selected_id)
    )

    if is_editing:
        st.info(f"Đang chỉnh sửa: **{current_rf_id}**")
        st.markdown("#### Cập nhật Reference Finding")
    else:
        st.markdown("#### Thêm Reference Finding mới")

    st.text_input("Mã định danh", value=current_rf_id, disabled=True)

    form_finding_text = st.text_input(
        "Mô tả Reference Finding chuẩn hóa",
        value=st.session_state.get("form_finding_text", ""),
        placeholder="Ví dụ: Đám mờ thùy trên phổi trái, tràn dịch màng phổi...",
    )
    st.session_state["form_finding_text"] = form_finding_text

    status_val = st.session_state.get("form_status", "Pending")
    status_idx = STATUS_CHOICES.index(status_val) if status_val in STATUS_CHOICES else 0
    form_status = st.selectbox(
        "Trạng thái",
        STATUS_CHOICES,
        index=status_idx,
        format_func=lambda s: STATUS_DISPLAY_MAP.get(s, s),
    )
    st.session_state["form_status"] = form_status

    form_boxes_key = f"form_boxes_input_{st.session_state.get('form_boxes_key_idx', 0)}"
    form_boxes_str = st.text_area(
        "Tọa độ khung định vị",
        value=st.session_state.get("form_boxes", "[]"),
        key=form_boxes_key,
        help="Tọa độ pixel trên ảnh gốc [x, y, w, h]. Tự động điền khi vẽ bằng chuột hoặc xóa khi xóa khung trên ảnh.",
    )

    btn_c1, btn_c2 = st.columns(2)
    with btn_c1:
        save_btn_label = "Cập nhật Reference Finding" if is_editing else "Lưu Reference Finding"
        save_clicked = st.button(save_btn_label, type="primary", use_container_width=True)
    with btn_c2:
        cancel_btn_label = "Hủy chỉnh sửa" if is_editing else "Làm mới biểu mẫu"
        reset_clicked = st.button(cancel_btn_label, use_container_width=True)

    if reset_clicked:
        _clear_form_state()
        if is_editing:
            st.session_state["pending_mode_switch"] = "Xem Reference Finding đã lưu"
        st.rerun()

    if save_clicked:
        if not form_finding_text.strip():
            st.error("Vui lòng nhập mô tả Reference Finding.")
            return

        try:
            parsed_b = parse_boxes(form_boxes_str)
        except Exception as err:
            st.error(f"Định dạng tọa độ khung không hợp lệ: {err}")
            return

        new_record = {
            "reference_finding_id": current_rf_id,
            "image_id": selected_id,
            "image_url": str(case_row.get("image_url", "")),
            "finding_text": form_finding_text.strip(),
            "status": form_status,
            "boxes": str(parsed_b),
        }

        if store.save_annotation(new_record):
            _clear_form_state()
            st.session_state["pending_mode_switch"] = "Xem Reference Finding đã lưu"
            st.rerun()
        else:
            st.error("Lỗi khi lưu vào cơ sở dữ liệu Google Sheets.")


def render(
    data: DatasetBundle,
    filtered: FilteredBundle,
    store: GoogleSheetsStore,
) -> None:
    """Render the Case Viewer and Interactive Annotation Studio."""
    st.subheader("Chi tiết ca bệnh và gán nhãn")
    st.caption("Xem chi tiết ca bệnh, báo cáo X-quang và thực hiện khoanh vùng Reference Finding.")

    master = filtered.master
    annotations = data.annotations

    case_ids = sorted(master["image_id"].dropna().unique().tolist()) if not master.empty else []
    if not case_ids:
        st.info("Không có ca bệnh nào phù hợp với bộ lọc hiện tại.")
        return

    if "target_case_id" in st.session_state:
        target_id = st.session_state.pop("target_case_id")
        if target_id in case_ids:
            st.session_state.current_case_idx = case_ids.index(target_id)
            st.session_state.query_case_handled = target_id

    query_case = str(st.query_params.get("case", "") or st.query_params.get("image_id", "")).strip()
    if query_case and query_case in case_ids and st.session_state.get("query_case_handled") != query_case:
        st.session_state.current_case_idx = case_ids.index(query_case)
        st.session_state.query_case_handled = query_case

    selected_id = _render_navigation(case_ids)

    # Keep URL query parameter synchronized with the currently inspected case ONLY if in Case Viewer tab
    if st.session_state.get("active_main_tab") == "Chi tiết ca bệnh":
        if st.query_params.get("case") != selected_id:
            st.query_params["case"] = selected_id

    if st.session_state.get("previous_case_id") != selected_id:
        st.session_state["previous_case_id"] = selected_id
        _clear_form_state()

    case_row = master[master["image_id"] == selected_id].iloc[0]
    case_findings = (
        annotations[annotations["image_id"] == selected_id].copy()
        if not annotations.empty
        else pd.DataFrame()
    )

    _render_kpi_summary(case_row, case_findings)

    left_col, right_col = st.columns([1.15, 1])

    img = get_case_image(case_row)
    if img is None:
        with left_col:
            st.subheader("Hình ảnh X-quang")
            st.warning(f"Không thể tải ảnh cho ca **{selected_id}**.")
            img_url = str(case_row.get("image_url", "")).strip()
            if img_url:
                st.markdown(f"[Mở ảnh trên Google Drive]({img_url})")
            else:
                st.info("Ca này chưa có link ảnh trên Google Sheets.")
        return

    orig_w, orig_h = img.size
    file_id = extract_drive_id(case_row.get("image_url"))

    with left_col:
        st.subheader("Hình ảnh X-quang")

        if "pending_mode_switch" in st.session_state:
            st.session_state["case_viewer_mode_radio"] = st.session_state.pop("pending_mode_switch")
        elif "case_viewer_mode_radio" not in st.session_state:
            st.session_state["case_viewer_mode_radio"] = "Xem Reference Finding đã lưu"

        mode = st.radio(
            "Chế độ hiển thị:",
            ["Xem Reference Finding đã lưu", "Chế độ vẽ bounding box"],
            horizontal=True,
            key="case_viewer_mode_radio",
        )

        is_editing = st.session_state.get("editing_rf_id") is not None
        if mode == "Xem Reference Finding đã lưu":
            view_findings = (
                case_findings[case_findings["reference_finding_id"] == st.session_state.editing_rf_id]
                if is_editing and not case_findings.empty
                else case_findings
            )
            _render_image_view(img, selected_id, file_id, view_findings, orig_w, orig_h)
        else:
            _render_canvas_view(img, selected_id, is_editing, orig_w, orig_h)

    with right_col:
        _render_clinical_context(selected_id, case_row)

        if not is_editing:
            _render_findings_list(case_findings, store)

        if mode == "Chế độ vẽ bounding box" or is_editing:
            _render_annotation_form(store, selected_id, case_row, is_editing)
