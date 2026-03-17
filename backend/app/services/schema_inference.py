"""
Schema Inference Service — analyze DataFrame to infer variable roles and types.
Used as context for LLM prompts and method routing.
"""
import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Thresholds
CATEGORICAL_UNIQUE_RATIO = 0.05  # < 5% unique values → likely categorical
CATEGORICAL_MAX_UNIQUE = 20  # absolute max unique for categorical


def infer_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze a DataFrame and return a structured schema.
    Returns:
        {
            "n_rows": int,
            "n_cols": int,
            "variables": [
                {
                    "name": str,
                    "dtype": str,
                    "role": "numeric" | "categorical" | "date" | "text" | "id",
                    "n_unique": int,
                    "n_missing": int,
                    "missing_pct": float,
                    "sample_values": list,
                }
            ],
            "numeric_vars": [str],
            "categorical_vars": [str],
            "summary_text": str,
        }
    """
    variables = []
    numeric_vars = []
    categorical_vars = []

    for col in df.columns:
        series = df[col]
        n_unique = int(series.nunique())
        n_missing = int(series.isna().sum())
        missing_pct = round(n_missing / len(df) * 100, 1) if len(df) > 0 else 0.0

        # Sample values (up to 5, excluding NaN)
        sample = series.dropna().head(5).tolist()
        sample = [s.item() if hasattr(s, 'item') else s for s in sample]

        # Role detection
        role = _infer_role(series, n_unique, len(df), col)

        variables.append({
            "name": col,
            "dtype": str(series.dtype),
            "role": role,
            "n_unique": n_unique,
            "n_missing": n_missing,
            "missing_pct": missing_pct,
            "sample_values": sample[:5],
        })

        if role == "numeric":
            numeric_vars.append(col)
        elif role == "categorical":
            categorical_vars.append(col)

    summary = _build_summary_text(df, numeric_vars, categorical_vars)

    return {
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "variables": variables,
        "numeric_vars": numeric_vars,
        "categorical_vars": categorical_vars,
        "summary_text": summary,
    }


def _infer_role(series: pd.Series, n_unique: int, n_total: int, col_name: str) -> str:
    """Infer variable role from data characteristics."""
    name_lower = col_name.lower()

    # ID-like columns
    if n_unique == n_total and n_total > 10:
        return "id"
    if name_lower in ("id", "index", "row", "stt", "ma"):
        return "id"

    # Date columns
    if pd.api.types.is_datetime64_dtype(series):
        return "date"

    # Numeric
    if pd.api.types.is_numeric_dtype(series):
        unique_ratio = n_unique / n_total if n_total > 0 else 0
        if n_unique <= CATEGORICAL_MAX_UNIQUE and unique_ratio < CATEGORICAL_UNIQUE_RATIO:
            return "categorical"  # coded categorical (e.g., gender=1/2)
        if n_unique <= 2:
            return "categorical"  # binary
        return "numeric"

    # String
    if n_unique <= CATEGORICAL_MAX_UNIQUE:
        return "categorical"

    return "text"


def _build_summary_text(df: pd.DataFrame, numeric: List[str], categorical: List[str]) -> str:
    """Build human-readable dataset summary for LLM context."""
    parts = [
        f"Dataset: {len(df)} rows × {len(df.columns)} columns.",
        f"Numeric variables ({len(numeric)}): {', '.join(numeric[:10])}{'...' if len(numeric) > 10 else ''}.",
        f"Categorical variables ({len(categorical)}): {', '.join(categorical[:10])}{'...' if len(categorical) > 10 else ''}.",
    ]

    # Basic stats for numeric
    if numeric:
        desc = df[numeric].describe().round(2)
        for var in numeric[:3]:
            parts.append(
                f"  {var}: mean={desc.loc['mean', var]}, "
                f"std={desc.loc['std', var]}, "
                f"range=[{desc.loc['min', var]}, {desc.loc['max', var]}]"
            )

    return "\n".join(parts)
