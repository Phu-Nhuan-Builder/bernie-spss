"""
Descriptive Statistics Service
Pure statistical functions — no HTTP concerns
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def compute_frequencies(df: pd.DataFrame, variable: str, value_labels: Optional[Dict] = None) -> dict:
    """
    Compute frequency table with counts, percentages, cumulative %.
    Matches SPSS Frequencies output.
    """
    series = df[variable]
    n_total = len(series)
    n_missing = int(series.isna().sum())
    n_valid = n_total - n_missing

    value_counts = series.value_counts(dropna=True).sort_index()
    value_labels = value_labels or {}

    rows_detail = []
    table_rows = []
    cumul = 0.0
    for val, count in value_counts.items():
        pct = (count / n_total) * 100
        valid_pct = (count / n_valid) * 100 if n_valid > 0 else 0.0
        cumul += valid_pct
        label = value_labels.get(str(val), str(val))
        rows_detail.append({
            "value": val,
            "label": label,
            "count": int(count),
            "percent": round(pct, 1),
            "valid_percent": round(valid_pct, 1),
            "cumulative_percent": round(cumul, 1),
        })
        table_rows.append([val, label, int(count), round(pct, 1), round(valid_pct, 1), round(cumul, 1)])

    # Add missing row if applicable
    if n_missing > 0:
        missing_pct = (n_missing / n_total) * 100
        rows_detail.append({
            "value": "Missing",
            "label": "System",
            "count": n_missing,
            "percent": round(missing_pct, 1),
            "valid_percent": 0.0,
            "cumulative_percent": 100.0,
        })
        table_rows.append(["Missing", "System", n_missing, round(missing_pct, 1), 0.0, 100.0])

    # Mode
    mode_result = None
    try:
        mode_result = float(series.mode().iloc[0]) if len(series.mode()) > 0 else None
    except Exception:
        pass

    return {
        "variable": variable,
        "label": value_labels.get("_label", ""),
        "rows": table_rows,
        "row_details": rows_detail,
        "n_valid": n_valid,
        "n_missing": n_missing,
        "n_total": n_total,
        "mode": mode_result,
        "headers": ["Value", "Label", "Count", "Percent", "Valid %", "Cumul. %"],
    }


def compute_descriptives(df: pd.DataFrame, variables: List[str]) -> dict:
    """
    Compute descriptive statistics for numeric variables.
    Matches SPSS Descriptives output.
    """
    rows = []
    for var in variables:
        if var not in df.columns:
            continue
        series = df[var].dropna()
        n = len(series)
        if n == 0:
            continue

        arr = series.to_numpy(dtype=float)
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
        variance = float(np.var(arr, ddof=1)) if n > 1 else 0.0
        minimum = float(np.min(arr))
        maximum = float(np.max(arr))
        rng = maximum - minimum
        median = float(np.median(arr))
        total = float(np.sum(arr))
        se_mean = std / np.sqrt(n) if n > 0 else 0.0

        # Skewness and kurtosis (SPSS uses Fisher's formulation with bias correction)
        skewness = float(stats.skew(arr, bias=False)) if n >= 3 else None
        kurtosis = float(stats.kurtosis(arr, bias=False, fisher=True)) if n >= 4 else None

        # Standard error of skewness and kurtosis
        se_skew = None
        se_kurt = None
        if n >= 3:
            se_skew = float(np.sqrt(6.0 * n * (n - 1) / ((n - 2) * (n + 1) * (n + 3))))
        if n >= 4:
            se_kurt = float(np.sqrt(24.0 * n * (n - 1)**2 / ((n - 3) * (n - 2) * (n + 3) * (n + 5))))

        rows.append({
            "variable": var,
            "label": "",
            "n": n,
            "mean": round(mean, 4),
            "std_dev": round(std, 4),
            "variance": round(variance, 4),
            "minimum": round(minimum, 4),
            "maximum": round(maximum, 4),
            "range": round(rng, 4),
            "skewness": round(skewness, 4) if skewness is not None else None,
            "std_error_skew": round(se_skew, 4) if se_skew is not None else None,
            "kurtosis": round(kurtosis, 4) if kurtosis is not None else None,
            "std_error_kurt": round(se_kurt, 4) if se_kurt is not None else None,
            "se_mean": round(se_mean, 4),
            "median": round(median, 4),
            "sum": round(total, 4),
        })

    return {
        "rows": rows,
        "headers": ["Variable", "N", "Mean", "Std Dev", "Variance", "Min", "Max", "Range", "Skewness", "Kurtosis"],
    }


def compute_crosstabs(
    df: pd.DataFrame, row_var: str, col_var: str,
    row_value_labels: Optional[Dict] = None,
    col_value_labels: Optional[Dict] = None
) -> dict:
    """
    Compute crosstabulation with chi-square, Cramer's V, Phi, Fisher's exact.
    Matches SPSS Crosstabs output.
    """
    row_value_labels = row_value_labels or {}
    col_value_labels = col_value_labels or {}

    # Build crosstab
    ct = pd.crosstab(df[row_var], df[col_var], margins=True, margins_name="Total")
    n = int(ct.loc["Total", "Total"])

    # Chi-square (on the data without margins)
    ct_data = pd.crosstab(df[row_var], df[col_var])
    chi2 = None
    df_chi2 = None
    p_value = None
    cramers_v = None
    phi = None
    fisher_p = None

    try:
        chi2_val, p_val, dof, _ = stats.chi2_contingency(ct_data.values, correction=False)
        chi2 = round(float(chi2_val), 4)
        df_chi2 = int(dof)
        p_value = round(float(p_val), 4)

        # Cramer's V
        r, c = ct_data.shape
        min_dim = min(r - 1, c - 1)
        if min_dim > 0 and n > 0:
            cramers_v = round(float(np.sqrt(chi2_val / (n * min_dim))), 4)

        # Phi (only meaningful for 2x2)
        if r == 2 and c == 2:
            phi = round(float(np.sqrt(chi2_val / n)), 4)

        # Fisher's exact (only for 2x2)
        if r == 2 and c == 2:
            _, fisher_p_val = stats.fisher_exact(ct_data.values)
            fisher_p = round(float(fisher_p_val), 4)
    except Exception as e:
        logger.warning(f"Chi-square failed: {e}")

    # Convert crosstab to serializable format
    table = {}
    for row_idx in ct.index:
        row_label = row_value_labels.get(str(row_idx), str(row_idx))
        table[row_label] = {}
        for col_idx in ct.columns:
            col_label = col_value_labels.get(str(col_idx), str(col_idx))
            table[row_label][col_label] = int(ct.loc[row_idx, col_idx])

    return {
        "row_var": row_var,
        "col_var": col_var,
        "table": table,
        "chi2": chi2,
        "df": df_chi2,
        "p_value": p_value,
        "cramers_v": cramers_v,
        "phi": phi,
        "fisher_exact_p": fisher_p,
        "n": n,
        "headers": [col_var] + [str(c) for c in ct_data.columns] + ["Total"],
        "rows": (
            [
                [str(r)] + [int(ct_data.loc[r, c]) if r in ct_data.index and c in ct_data.columns else 0 for c in ct_data.columns] + [int(ct.loc[r, "Total"]) if r in ct.index else 0]
                for r in ct_data.index
            ] + [["Total"] + [int(ct.loc["Total", c]) for c in ct_data.columns] + [n]]
        ),
    }


def spss_boxplot_stats(data: list) -> dict:
    """
    SPSS-exact box plot whisker statistics.
    Whiskers are ACTUAL DATA POINTS (adjacent values), not fence boundaries.
    Tukey (1977) Exploratory Data Analysis.
    """
    arr = np.array([x for x in data if x is not None and not np.isnan(float(x))], dtype=float)
    if len(arr) == 0:
        return {}

    q1 = float(np.percentile(arr, 25))  # SPSS weighted average (numpy default matches)
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outer_lower = q1 - 3.0 * iqr
    outer_upper = q3 + 3.0 * iqr

    # EXACT: use actual data points nearest the fences
    lower_adjacent = float(arr[arr >= lower_fence].min()) if len(arr[arr >= lower_fence]) > 0 else q1
    upper_adjacent = float(arr[arr <= upper_fence].max()) if len(arr[arr <= upper_fence]) > 0 else q3

    mild_outliers = arr[(arr < lower_fence) | (arr > upper_fence)]
    mild_outliers = mild_outliers[(mild_outliers >= outer_lower) & (mild_outliers <= outer_upper)]
    extreme_outliers = arr[(arr < outer_lower) | (arr > outer_upper)]

    return {
        "q1": round(q1, 4),
        "median": round(float(np.median(arr)), 4),
        "q3": round(q3, 4),
        "whisker_low": round(lower_adjacent, 4),
        "whisker_high": round(upper_adjacent, 4),
        "mild_outliers": mild_outliers.tolist(),   # SPSS shows as ○
        "extreme_outliers": extreme_outliers.tolist(),  # SPSS shows as ★
    }


def compute_explore(df: pd.DataFrame, variable: str) -> dict:
    """
    Compute Explore statistics: Shapiro-Wilk, percentiles, box plot stats.
    Matches SPSS Explore output.
    """
    series = df[variable].dropna()
    n_valid = len(series)
    n_missing = int(df[variable].isna().sum())
    arr = series.to_numpy(dtype=float)

    # Shapiro-Wilk normality test
    shapiro_w = None
    shapiro_p = None
    if 3 <= n_valid <= 5000:
        try:
            w, p = stats.shapiro(arr)
            shapiro_w = round(float(w), 4)
            shapiro_p = round(float(p), 4)
        except Exception:
            pass

    # Percentiles
    percentiles = {}
    for p in [5, 10, 25, 50, 75, 90, 95]:
        percentiles[str(p)] = round(float(np.percentile(arr, p)), 4)

    # Box plot stats (SPSS-exact)
    boxplot_stats = spss_boxplot_stats(arr.tolist())

    return {
        "variable": variable,
        "n_valid": n_valid,
        "n_missing": n_missing,
        "shapiro_w": shapiro_w,
        "shapiro_p": shapiro_p,
        "boxplot_stats": boxplot_stats,
        "percentiles": percentiles,
    }
