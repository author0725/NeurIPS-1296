"""
canonical_extractors.py — Pull values from canonical CSV/JSON depository.

Each extractor is a callable that, given a depository root path, returns a
Python value. Pair with `paper_extractors` extractors in `verifier_core` to
verify paper-vs-canonical agreement at runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


# Lazy pandas import
_PD = None
def _pd():
    global _PD
    if _PD is None:
        import pandas as pd
        _PD = pd
    return _PD


def _load_csv(path: Path):
    return _pd().read_csv(path)


def _load_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)


# =============================================================================
# CSV extractors
# =============================================================================
def csv_cell(rel_path: str, filter_dict: dict, column: str) -> Callable:
    """Filter rows by `filter_dict` (column->value), return df[column] of unique match."""
    def _extract(dep_root: Path):
        path = dep_root / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Canonical file missing: {rel_path}")
        df = _load_csv(path)
        mask = _pd().Series(True, index=df.index)
        for col, val in filter_dict.items():
            mask &= (df[col] == val)
        sub = df[mask]
        if len(sub) == 0:
            raise KeyError(f"No row matches {filter_dict} in {rel_path}")
        if len(sub) > 1:
            raise KeyError(f"Multiple rows ({len(sub)}) match {filter_dict} in {rel_path}")
        return sub.iloc[0][column]
    return _extract


def csv_count(rel_path: str, filter_dict: dict, count_filter: dict) -> Callable:
    """Count rows matching count_filter within filter_dict subset."""
    def _extract(dep_root: Path):
        path = dep_root / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Canonical file missing: {rel_path}")
        df = _load_csv(path)
        mask = _pd().Series(True, index=df.index)
        for col, val in filter_dict.items():
            mask &= (df[col] == val)
        sub = df[mask]
        cm = _pd().Series(True, index=sub.index)
        for col, val in count_filter.items():
            if callable(val):
                cm &= sub[col].apply(val)
            else:
                cm &= (sub[col] == val)
        return int(cm.sum())
    return _extract


def csv_minmax(rel_path: str, filter_dict: dict, column: str, which: str) -> Callable:
    """min, max, or mean of `column` within filter."""
    def _extract(dep_root: Path):
        path = dep_root / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Canonical file missing: {rel_path}")
        df = _load_csv(path)
        mask = _pd().Series(True, index=df.index)
        for col, val in filter_dict.items():
            mask &= (df[col] == val)
        sub = df[mask]
        if which == "min":
            return float(sub[column].min())
        elif which == "max":
            return float(sub[column].max())
        elif which == "mean":
            return float(sub[column].mean())
        else:
            raise ValueError(f"Unknown which={which}")
    return _extract


def csv_minmax_pair(rel_path: str, filter_dict: dict, column: str) -> Callable:
    """Return (min, max) tuple of `column` within filter — for [lo, hi] range claims."""
    def _extract(dep_root: Path):
        path = dep_root / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Canonical file missing: {rel_path}")
        df = _load_csv(path)
        mask = _pd().Series(True, index=df.index)
        for col, val in filter_dict.items():
            mask &= (df[col] == val)
        sub = df[mask]
        return (float(sub[column].min()), float(sub[column].max()))
    return _extract


def csv_lambda(rel_path: str, fn: Callable) -> Callable:
    """Generic: apply `fn(df)` to a CSV. Use for custom aggregations."""
    def _extract(dep_root: Path):
        path = dep_root / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Canonical file missing: {rel_path}")
        df = _load_csv(path)
        return fn(df)
    return _extract


# =============================================================================
# JSON extractors
# =============================================================================
def json_path(rel_path: str, *keys) -> Callable:
    """Walk JSON via the given key path.

    For list elements, the key can be (list_key, filter_dict, target_field):
    finds the unique element of the list at list_key whose fields match
    filter_dict and returns target_field. (Pass list_key=None when the cursor
    is already the list.)
    """
    def _extract(dep_root: Path):
        path = dep_root / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Canonical file missing: {rel_path}")
        cur = _load_json(path)
        for k in keys:
            if isinstance(k, tuple) and len(k) == 3:
                list_key, filt, field_name = k
                if list_key is not None:
                    cur = cur[list_key]
                matches = [
                    item for item in cur
                    if all(item.get(fk) == fv for fk, fv in filt.items())
                ]
                if len(matches) != 1:
                    raise KeyError(f"Expected 1 match, got {len(matches)} for filter {filt}")
                cur = matches[0][field_name]
            elif isinstance(k, int):
                cur = cur[k]
            else:
                cur = cur[k]
        return cur
    return _extract
