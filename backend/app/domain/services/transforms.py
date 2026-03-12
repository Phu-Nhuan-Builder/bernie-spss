"""
Data Transform Service
Recode, Compute, Filter, Sort, Rank — pure DataFrame operations
"""
import logging
import re
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Safe namespace for pd.eval() expressions
_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "log": np.log,
    "log10": np.log10,
    "log2": np.log2,
    "exp": np.exp,
    "sqrt": np.sqrt,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "floor": np.floor,
    "ceil": np.ceil,
    "min": np.minimum,
    "max": np.maximum,
}

# Forbidden patterns in expressions (security)
_FORBIDDEN_PATTERNS = [
    r"import\s",
    r"__\w+__",
    r"exec\s*\(",
    r"eval\s*\(",
    r"open\s*\(",
    r"os\.",
    r"sys\.",
    r"subprocess",
    r"shutil",
    r"globals\s*\(",
    r"locals\s*\(",
]


def _sanitize_expression(expr: str) -> str:
    """Validate expression for safety. Raises ValueError if unsafe."""
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, expr, re.IGNORECASE):
            raise ValueError(f"Unsafe expression: forbidden pattern '{pattern}' detected")
    return expr


def recode_variable(
    df: pd.DataFrame,
    source_var: str,
    target_var: str,
    rules: List[Dict[str, Any]],
    else_value: Optional[Any] = None,
) -> pd.DataFrame:
    """
    Recode variable values via mapping rules.
    rules: list of {"from_value": ..., "to_value": ...}
    If target_var == source_var: recode into same variable.
    If else_value is None: unmapped values remain unchanged.
    """
    df = df.copy()

    if source_var not in df.columns:
        raise ValueError(f"Source variable '{source_var}' not found")

    # Build mapping dict
    mapping = {}
    for rule in rules:
        from_v = rule.get("from_value")
        to_v = rule.get("to_value")
        mapping[from_v] = to_v

    def apply_recode(val):
        if pd.isna(val):
            return mapping.get(None, val if else_value is None else else_value)
        for k, v in mapping.items():
            if k is not None and str(val) == str(k):
                return v
        if else_value is not None:
            return else_value
        return val  # keep original if no match and no else

    df[target_var] = df[source_var].apply(apply_recode)

    # Try to coerce numeric
    try:
        df[target_var] = pd.to_numeric(df[target_var], errors="ignore")
    except Exception:
        pass

    return df


def compute_variable(
    df: pd.DataFrame,
    target_var: str,
    expression: str,
    label: Optional[str] = None,
) -> pd.DataFrame:
    """
    Create a new variable via pd.eval() with safe namespace.
    expression examples: "var1 + var2 * 2", "log(income)", "age / 10"
    """
    df = df.copy()
    _sanitize_expression(expression)

    try:
        # Replace common math functions with numpy equivalents for eval
        result = df.eval(expression, local_dict=_SAFE_FUNCTIONS, engine="python")
        df[target_var] = result
    except Exception as e:
        raise ValueError(f"Expression evaluation failed: {str(e)}")

    return df


def select_cases(
    df: pd.DataFrame,
    condition: str,
    filter_type: str = "include",
) -> pd.DataFrame:
    """
    Filter rows using a condition string.
    Uses df.query() with sanitized input.
    filter_type: "include" keeps matching rows; "exclude" removes them.
    """
    _sanitize_expression(condition)

    try:
        mask = df.eval(condition, engine="python")
        if filter_type == "exclude":
            return df[~mask].copy().reset_index(drop=True)
        else:
            return df[mask].copy().reset_index(drop=True)
    except Exception as e:
        raise ValueError(f"Filter condition failed: {str(e)}")


def sort_cases(
    df: pd.DataFrame,
    sort_keys: List[Dict[str, str]],
) -> pd.DataFrame:
    """
    Sort DataFrame by multiple keys.
    sort_keys: [{"variable": "age", "order": "asc"}, {"variable": "gender", "order": "desc"}, ...]
    """
    df = df.copy()
    if not sort_keys:
        return df

    by = []
    ascending = []
    for key in sort_keys:
        var = key.get("variable", "")
        order = key.get("order", "asc").lower()
        if var not in df.columns:
            raise ValueError(f"Sort variable '{var}' not found")
        by.append(var)
        ascending.append(order != "desc")

    return df.sort_values(by=by, ascending=ascending).reset_index(drop=True)


def rank_cases(
    df: pd.DataFrame,
    variables: List[str],
    method: str = "average",
    ascending: bool = True,
) -> pd.DataFrame:
    """
    Rank variables using pandas rank().
    method: "average", "min", "max", "first", "dense"
    """
    df = df.copy()
    for var in variables:
        if var not in df.columns:
            raise ValueError(f"Variable '{var}' not found for ranking")
        rank_col = f"RANK_{var}"
        df[rank_col] = df[var].rank(method=method, ascending=ascending, na_option="keep")
    return df
