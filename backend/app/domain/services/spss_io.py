"""
SPSS I/O Service — Read/write .sav, .csv, .xlsx files
In-memory session store with TTL for MVP (single-dyno Render)
"""
import uuid
import math
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from datetime import datetime

import chardet
import pandas as pd
import numpy as np
from cachetools import TTLCache

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── In-memory session store with TTL auto-eviction ─────────────────────────────
# Key: session_id (str)
# Value: (DataFrame, DatasetMeta)
# Sessions auto-evict after TTL; cleared on process restart
SESSION_STORE: TTLCache = TTLCache(
    maxsize=settings.SESSION_MAX_COUNT,
    ttl=settings.SESSION_TTL_SECONDS,
)

VIETNAMESE_ENCODINGS = ["utf-8", "windows-1258", "windows-1252", "cp1258", "latin-1"]


def resolve_encoding(path: str, declared: Optional[str] = None) -> str:
    """Detect file encoding with Vietnamese fallback."""
    if declared and declared.lower() in ("utf-8", "utf8"):
        return "utf-8"
    try:
        with open(path, "rb") as f:
            raw = f.read(50_000)
        detection = chardet.detect(raw)
        if detection.get("confidence", 0) > 0.85:
            detected = detection.get("encoding", "windows-1258")
            if detected:
                return detected
    except Exception:
        pass
    return "windows-1258"  # Safe default for Vietnamese SPSS files


def _infer_var_type(series: pd.Series) -> str:
    """Infer SPSS variable type from pandas Series."""
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_dtype(series):
        return "date"
    return "string"


def _build_meta_from_df(df: pd.DataFrame, file_name: str, encoding: str = "utf-8") -> Any:
    """Build DatasetMeta from a plain DataFrame (no pyreadstat metadata)."""
    from app.domain.models.dataset import (
        DatasetMeta, VariableMeta, VariableType, VariableMeasure, VariableRole
    )
    variables = []
    for col in df.columns:
        var_type_str = _infer_var_type(df[col])
        var_type = VariableType(var_type_str)
        measure = VariableMeasure.scale if var_type == VariableType.numeric else VariableMeasure.nominal
        width = 8 if var_type == VariableType.numeric else min(255, int(df[col].astype(str).str.len().max() or 8))
        decimals = 2 if var_type == VariableType.numeric else 0
        variables.append(VariableMeta(
            name=str(col),
            label="",
            var_type=var_type,
            width=width,
            decimals=decimals,
            value_labels={},
            missing_values=[],
            measure=measure,
            role=VariableRole.input,
        ))
    return DatasetMeta(
        file_name=file_name,
        n_cases=len(df),
        n_vars=len(df.columns),
        variables=variables,
        encoding=encoding,
    )


def read_sav(path: str) -> Tuple[pd.DataFrame, Any]:
    """Read SPSS .sav file using pyreadstat with full metadata."""
    import pyreadstat
    from app.domain.models.dataset import (
        DatasetMeta, VariableMeta, VariableType, VariableMeasure, VariableRole
    )

    df, meta = pyreadstat.read_sav(
        path,
        apply_value_formats=False,  # Keep numeric codes for computation
        formats_as_category=True,   # Memory efficient
    )

    # Build VariableMeta list from pyreadstat metadata
    variables = []
    for col in meta.column_names:
        # Variable type
        var_type_str = _infer_var_type(df[col])
        var_type = VariableType(var_type_str)

        # Label
        label = meta.column_names_to_labels.get(col, "") or ""

        # Value labels — convert keys to strings
        raw_vl = meta.variable_value_labels.get(col, {}) or {}
        value_labels = {str(k): str(v) for k, v in raw_vl.items()}

        # Missing values
        missing = []
        if hasattr(meta, "missing_ranges") and col in meta.missing_ranges:
            for mr in meta.missing_ranges[col]:
                if mr.get("lo") == mr.get("hi"):
                    missing.append(mr["lo"])

        # Measure
        measure_map = {"nominal": "nominal", "ordinal": "ordinal", "scale": "scale", "unknown": "scale"}
        raw_measure = ""
        if hasattr(meta, "variable_measure"):
            raw_measure = meta.variable_measure.get(col, "") or ""
        measure = VariableMeasure(measure_map.get(raw_measure.lower(), "scale"))

        # Width / decimals
        width = 8
        decimals = 2 if var_type == VariableType.numeric else 0
        if hasattr(meta, "column_widths") and col in (meta.column_widths or {}):
            width = meta.column_widths[col] or 8

        variables.append(VariableMeta(
            name=col,
            label=label,
            var_type=var_type,
            width=width,
            decimals=decimals,
            value_labels=value_labels,
            missing_values=missing,
            measure=measure,
            role=VariableRole.input,
        ))

    dataset_meta = DatasetMeta(
        file_name=Path(path).name,
        n_cases=len(df),
        n_vars=len(df.columns),
        variables=variables,
        encoding=meta.file_encoding or "utf-8",
    )
    return df, dataset_meta


def read_csv(path: str, encoding: Optional[str] = None) -> Tuple[pd.DataFrame, Any]:
    """Read CSV file with encoding detection."""
    if not encoding:
        encoding = resolve_encoding(path)
    try:
        df = pd.read_csv(path, encoding=encoding, na_values=["", "NA", "N/A", "nan", "NaN", "."])
    except UnicodeDecodeError:
        # Fallback to latin-1 which reads anything
        df = pd.read_csv(path, encoding="latin-1", na_values=["", "NA", "N/A", "nan", "NaN", "."])
    meta = _build_meta_from_df(df, Path(path).name, encoding)
    return df, meta


def read_excel(path: str) -> Tuple[pd.DataFrame, Any]:
    """Read Excel file (.xlsx/.xls)."""
    df = pd.read_excel(path, na_values=["", "NA", "N/A", "nan", "NaN", "."])
    meta = _build_meta_from_df(df, Path(path).name, "utf-8")
    return df, meta


def read_file(path: str, file_ext: str) -> Tuple[pd.DataFrame, Any]:
    """Dispatch file reading based on extension."""
    ext = file_ext.lower().lstrip(".")
    if ext == "sav":
        return read_sav(path)
    elif ext == "csv":
        return read_csv(path)
    elif ext in ("xlsx", "xls"):
        return read_excel(path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def write_sav(df: pd.DataFrame, meta: Any, path: str) -> None:
    """Write DataFrame back to .sav with metadata round-trip."""
    import pyreadstat

    # Build pyreadstat metadata dicts
    column_labels = {}
    variable_value_labels = {}
    variable_measure = {}

    for v in meta.variables:
        column_labels[v.name] = v.label or ""
        if v.value_labels:
            # Convert string keys back to numeric where possible
            vl = {}
            for k, lbl in v.value_labels.items():
                try:
                    vl[float(k)] = lbl
                except (ValueError, TypeError):
                    vl[k] = lbl
            variable_value_labels[v.name] = vl
        variable_measure[v.name] = v.measure.value

    pyreadstat.write_sav(
        df,
        path,
        column_labels=column_labels,
        variable_value_labels=variable_value_labels,
        variable_measure=variable_measure,
    )


def df_to_json_safe(df: pd.DataFrame) -> list:
    """Serialize DataFrame to list of dicts, handling NaN, datetime, numpy types."""
    records = []
    for _, row in df.iterrows():
        record = {}
        for col, val in row.items():
            if isinstance(val, float) and math.isnan(val):
                record[col] = None
            elif isinstance(val, (np.integer,)):
                record[col] = int(val)
            elif isinstance(val, (np.floating,)):
                record[col] = None if math.isnan(float(val)) else float(val)
            elif isinstance(val, (np.bool_,)):
                record[col] = bool(val)
            elif isinstance(val, pd.Timestamp):
                record[col] = val.isoformat()
            elif isinstance(val, (pd.NA.__class__, type(pd.NaT))):
                record[col] = None
            else:
                try:
                    # Check for pd.NA
                    if pd.isna(val):
                        record[col] = None
                    else:
                        record[col] = val
                except (TypeError, ValueError):
                    record[col] = val
        records.append(record)
    return records


def create_session(df: pd.DataFrame, meta: Any) -> str:
    """Create a new session and store in SESSION_STORE. Returns session_id."""
    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = (df, meta)
    logger.info(f"Created session {session_id}: {meta.n_cases} cases × {meta.n_vars} vars")
    return session_id


def get_session(session_id: str) -> Tuple[pd.DataFrame, Any]:
    """Retrieve (df, meta) from SESSION_STORE. Raises SessionNotFoundError if missing."""
    from app.core.exceptions import SessionNotFoundError
    if session_id not in SESSION_STORE:
        raise SessionNotFoundError(session_id)
    return SESSION_STORE[session_id]


def update_session(session_id: str, df: pd.DataFrame, meta: Any) -> None:
    """Update session in SESSION_STORE."""
    from app.core.exceptions import SessionNotFoundError
    if session_id not in SESSION_STORE:
        raise SessionNotFoundError(session_id)
    SESSION_STORE[session_id] = (df, meta)


def delete_session(session_id: str) -> None:
    """Remove session from SESSION_STORE."""
    SESSION_STORE.pop(session_id, None)
