from __future__ import annotations

from src.models import DatasetBundle, FilteredBundle, FilterSelection


def apply_filters(data: DatasetBundle, selection: FilterSelection) -> FilteredBundle:
    """Filter master cases and linked annotations based on global sidebar selections."""
    master = data.master.copy()

    if selection.splits and "split" in master.columns:
        master = master[master["split"].astype(str).isin(selection.splits)]

    if selection.sexes and "sex" in master.columns:
        master = master[master["sex"].astype(str).isin(selection.sexes)]

    if selection.views and "view" in master.columns:
        master = master[master["view"].astype(str).isin(selection.views)]

    # Filter linked annotations
    if not data.annotations.empty and "image_id" in data.annotations.columns:
        valid_ids = set(master["image_id"].dropna().unique())
        annotations = data.annotations[data.annotations["image_id"].isin(valid_ids)].copy()
    else:
        annotations = data.annotations.copy()

    return FilteredBundle(master=master, annotations=annotations)
