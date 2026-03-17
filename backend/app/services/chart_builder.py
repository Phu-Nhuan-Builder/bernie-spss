"""
Chart Builder — Generate chart JSON specs from statistical results.
Returns specs compatible with frontend Plotly/Recharts rendering.
"""
from typing import Any, Dict, List, Optional


def build_charts(method: str, results: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build chart specs from statistical results. Returns list of chart specs."""
    charts: List[Dict[str, Any]] = []

    if method == "descriptives":
        charts.extend(_charts_descriptives(results, params))
    elif method == "frequencies":
        charts.extend(_charts_frequencies(results, params))
    elif method == "explore":
        charts.extend(_charts_explore(results, params))
    elif method == "independent_ttest":
        charts.extend(_charts_ttest(results, params))
    elif method == "one_way_anova":
        charts.extend(_charts_anova(results, params))
    elif method == "correlation":
        charts.extend(_charts_correlation(results, params))
    elif method == "ols_regression":
        charts.extend(_charts_regression(results, params))
    elif method == "binary_logistic":
        charts.extend(_charts_logistic(results, params))
    elif method == "factor_analysis":
        charts.extend(_charts_factor(results, params))
    elif method == "crosstabs":
        charts.extend(_charts_crosstabs(results, params))

    return charts


def _charts_descriptives(r: Dict, p: Dict) -> List[Dict]:
    """Bar chart of means across variables, or comparison chart for entity comparison."""
    # Handle entity comparison format
    if r.get("comparison"):
        group_names = r.get("group_names", [])
        comparison_rows = r.get("comparison_rows", [])
        if not comparison_rows or not group_names:
            return []

        charts = []
        # One chart per variable showing values for each entity
        for row in comparison_rows:
            var_name = row[0]
            values = row[1:]
            charts.append({
                "chart_type": "bar",
                "title": f"{var_name} — Comparison",
                "x": group_names,
                "y": [v if isinstance(v, (int, float)) else 0 for v in values],
                "x_label": r.get("grouped_by", "Group"),
                "y_label": var_name,
            })
        return charts

    # Standard descriptives
    headers = r.get("headers", [])
    rows = r.get("rows", [])
    if not rows:
        return []

    variables = [row[0] if isinstance(row, list) else row.get("variable", "") for row in rows]
    means = []
    for row in rows:
        if isinstance(row, list):
            mean_idx = headers.index("Mean") if "Mean" in headers else 1
            means.append(row[mean_idx] if mean_idx < len(row) else 0)
        else:
            means.append(row.get("mean", 0))

    return [{
        "chart_type": "bar",
        "title": "Descriptive Statistics — Means",
        "x": variables,
        "y": means,
        "x_label": "Variable",
        "y_label": "Mean",
    }]


def _charts_frequencies(r: Dict, p: Dict) -> List[Dict]:
    """Histogram/bar chart from frequency counts."""
    row_details = r.get("row_details", [])
    if not row_details:
        rows = r.get("rows", [])
        if not rows:
            return []
        labels = [str(row[0] if isinstance(row, list) else row.get("value", "")) for row in rows]
        counts = [row[2] if isinstance(row, list) and len(row) > 2 else row.get("count", 0) for row in rows]
    else:
        labels = [str(rd.get("value", "")) for rd in row_details]
        counts = [rd.get("count", 0) for rd in row_details]

    return [{
        "chart_type": "bar",
        "title": f"Frequency Distribution — {r.get('variable', '')}",
        "x": labels,
        "y": counts,
        "x_label": str(r.get("variable", "Value")),
        "y_label": "Frequency",
    }]


def _charts_explore(r: Dict, p: Dict) -> List[Dict]:
    """Box plot from explore results."""
    bs = r.get("boxplot_stats")
    if not bs:
        return []
    return [{
        "chart_type": "boxplot",
        "title": f"Box Plot — {r.get('variable', '')}",
        "data": {
            "q1": bs.get("q1"),
            "median": bs.get("median"),
            "q3": bs.get("q3"),
            "whisker_low": bs.get("whisker_low"),
            "whisker_high": bs.get("whisker_high"),
            "mild_outliers": bs.get("mild_outliers", []),
            "extreme_outliers": bs.get("extreme_outliers", []),
        },
    }]


def _charts_ttest(r: Dict, p: Dict) -> List[Dict]:
    """Group comparison bar chart."""
    gs = r.get("group_stats", [])
    if not gs:
        return []
    return [{
        "chart_type": "bar",
        "title": "Group Comparison — Means",
        "x": [str(g.get("group", "")) for g in gs],
        "y": [g.get("mean", 0) for g in gs],
        "error_y": [g.get("std", 0) for g in gs],
        "x_label": p.get("group_var", "Group"),
        "y_label": f"Mean of {p.get('test_var', 'Variable')}",
    }]


def _charts_anova(r: Dict, p: Dict) -> List[Dict]:
    """Group means bar chart for ANOVA."""
    gs = r.get("group_stats", [])
    if not gs:
        return []
    return [{
        "chart_type": "bar",
        "title": f"ANOVA — Mean {p.get('dep_var', '')} by {p.get('group_var', '')}",
        "x": [str(g.get("group", "")) for g in gs],
        "y": [g.get("mean", 0) for g in gs],
        "error_y": [g.get("std", 0) for g in gs],
        "x_label": p.get("group_var", "Group"),
        "y_label": f"Mean {p.get('dep_var', '')}",
    }]


def _charts_correlation(r: Dict, p: Dict) -> List[Dict]:
    """Correlation heatmap."""
    variables = r.get("variables", [])
    r_matrix = r.get("r_matrix", [])
    if not variables or not r_matrix:
        return []
    return [{
        "chart_type": "heatmap",
        "title": f"Correlation Matrix ({r.get('method', 'pearson')})",
        "x_labels": variables,
        "y_labels": variables,
        "z": r_matrix,
        "color_scale": "RdBu",
    }]


def _charts_regression(r: Dict, p: Dict) -> List[Dict]:
    """Coefficient bar chart + residual scatter."""
    charts = []
    coeffs = r.get("coefficients", [])
    if coeffs:
        vars_list = [str(c.get("variable", "")) for c in coeffs if c.get("variable") != "(Intercept)"]
        betas = [c.get("beta", 0) or 0 for c in coeffs if c.get("variable") != "(Intercept)"]
        if vars_list:
            charts.append({
                "chart_type": "bar",
                "title": "Standardized Coefficients (β)",
                "x": vars_list,
                "y": betas,
                "x_label": "Predictor",
                "y_label": "β (Standardized)",
            })

    residuals = r.get("residuals_data")
    if residuals:
        charts.append({
            "chart_type": "scatter",
            "title": "Residuals vs Leverage",
            "x": residuals.get("leverage", []),
            "y": residuals.get("standardized_residuals", []),
            "x_label": "Leverage",
            "y_label": "Standardized Residuals",
        })
    return charts


def _charts_logistic(r: Dict, p: Dict) -> List[Dict]:
    """Odds ratio forest plot data."""
    coeffs = r.get("coefficients", [])
    if not coeffs:
        return []
    vars_list = [str(c.get("variable", "")) for c in coeffs if c.get("variable") != "(Intercept)"]
    exp_b = [c.get("exp_B", 1) for c in coeffs if c.get("variable") != "(Intercept)"]
    return [{
        "chart_type": "bar",
        "title": "Odds Ratios — Exp(B)",
        "x": vars_list,
        "y": exp_b,
        "x_label": "Predictor",
        "y_label": "Exp(B) / Odds Ratio",
        "reference_line": 1.0,
    }]


def _charts_factor(r: Dict, p: Dict) -> List[Dict]:
    """Scree plot from eigenvalues."""
    eigenvalues = r.get("eigenvalues", [])
    if not eigenvalues:
        return []
    return [{
        "chart_type": "line",
        "title": "Scree Plot",
        "x": list(range(1, len(eigenvalues) + 1)),
        "y": eigenvalues,
        "x_label": "Factor",
        "y_label": "Eigenvalue",
        "reference_line": 1.0,
    }]


def _charts_crosstabs(r: Dict, p: Dict) -> List[Dict]:
    """Stacked bar from crosstab."""
    headers = r.get("headers", [])
    rows = r.get("rows", [])
    if not headers or not rows:
        return []
    return [{
        "chart_type": "bar",
        "title": f"Cross-Tabulation — {p.get('row_var', '')} × {p.get('col_var', '')}",
        "x": [str(row[0]) if isinstance(row, list) else "" for row in rows],
        "y": [row[1] if isinstance(row, list) and len(row) > 1 else 0 for row in rows],
        "x_label": p.get("row_var", ""),
        "y_label": "Count",
    }]
