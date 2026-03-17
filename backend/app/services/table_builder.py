"""
Table Builder — Format statistical results into structured table data.
Returns { columns: [...], rows: [...] } for frontend rendering.
"""
from typing import Any, Dict, List


def build_tables(method: str, results: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build structured table data from statistical results."""
    tables: List[Dict[str, Any]] = []

    if method == "descriptives":
        tables.extend(_tables_descriptives(results))
    elif method == "frequencies":
        tables.extend(_tables_frequencies(results))
    elif method == "crosstabs":
        tables.extend(_tables_crosstabs(results))
    elif method == "explore":
        tables.extend(_tables_explore(results))
    elif method == "independent_ttest":
        tables.extend(_tables_ttest_independent(results))
    elif method == "one_way_anova":
        tables.extend(_tables_anova(results))
    elif method == "correlation":
        tables.extend(_tables_correlation(results))
    elif method == "ols_regression":
        tables.extend(_tables_regression(results))
    elif method == "binary_logistic":
        tables.extend(_tables_logistic(results))
    elif method == "reliability":
        tables.extend(_tables_reliability(results))
    elif method == "factor_analysis":
        tables.extend(_tables_factor(results))

    return tables


def _safe_rows(results: Dict, default_headers: List[str] = None) -> Dict:
    """Extract headers/rows from results, with fallback."""
    headers = results.get("headers", default_headers or [])
    rows = results.get("rows", [])
    return {"columns": headers, "rows": rows}


def _tables_descriptives(r: Dict) -> List[Dict]:
    # Handle entity comparison format
    if r.get("comparison"):
        group_names = r.get("group_names", [])
        comparison_rows = r.get("comparison_rows", [])
        if not comparison_rows or not group_names:
            return []
        return [{
            "title": f"Comparison by {r.get('grouped_by', 'Group')}",
            "columns": ["Variable"] + group_names,
            "rows": comparison_rows,
        }]

    # Standard descriptives table
    headers = r.get("headers", ["Variable", "N", "Mean", "Std. Deviation", "Minimum", "Maximum", "Skewness", "Kurtosis"])
    rows = r.get("rows", [])
    return [{"title": "Descriptive Statistics", "columns": headers, "rows": rows}]


def _tables_frequencies(r: Dict) -> List[Dict]:
    headers = r.get("headers", ["Value", "Label", "Frequency", "Percent", "Valid Percent", "Cumulative Percent"])
    rows = r.get("rows", [])
    tables = [{"title": f"Frequency Table — {r.get('variable', '')}", "columns": headers, "rows": rows}]

    # Summary stats
    tables.append({
        "title": "Statistics",
        "columns": ["Statistic", "Value"],
        "rows": [
            ["N Valid", r.get("n_valid")],
            ["Missing", r.get("n_missing")],
            ["Mode", r.get("mode")],
        ],
    })
    return tables


def _tables_crosstabs(r: Dict) -> List[Dict]:
    headers = r.get("headers", [])
    rows = r.get("rows", [])
    tables = [{"title": "Crosstabulation", "columns": headers, "rows": rows}]

    # Chi-square test
    chi_rows = []
    if r.get("chi2") is not None:
        chi_rows.append(["Pearson Chi-Square", r.get("chi2"), r.get("p_value")])
    if r.get("fisher_exact_p") is not None:
        chi_rows.append(["Fisher's Exact Test", None, r.get("fisher_exact_p")])
    if chi_rows:
        tables.append({
            "title": "Chi-Square Tests",
            "columns": ["Test", "Value", "Asymptotic Sig."],
            "rows": chi_rows,
        })

    # Effect size
    if r.get("cramers_v") is not None:
        tables.append({
            "title": "Symmetric Measures",
            "columns": ["Measure", "Value"],
            "rows": [
                ["Cramér's V", r.get("cramers_v")],
                ["Phi", r.get("phi")],
                ["N", r.get("n")],
            ],
        })
    return tables


def _tables_explore(r: Dict) -> List[Dict]:
    tables = [{
        "title": "Normality Test — Shapiro-Wilk",
        "columns": ["Statistic", "N Valid", "Sig."],
        "rows": [[r.get("shapiro_w"), r.get("n_valid"), r.get("shapiro_p")]],
    }]

    # Percentiles
    pctiles = r.get("percentiles")
    if pctiles:
        tables.append({
            "title": "Percentiles",
            "columns": [f"P{k}" for k in pctiles.keys()],
            "rows": [list(pctiles.values())],
        })

    # Boxplot stats
    bs = r.get("boxplot_stats")
    if bs:
        tables.append({
            "title": "Box Plot Statistics",
            "columns": ["Statistic", "Value"],
            "rows": [
                ["Q1", bs.get("q1")],
                ["Median", bs.get("median")],
                ["Q3", bs.get("q3")],
                ["Whisker Low", bs.get("whisker_low")],
                ["Whisker High", bs.get("whisker_high")],
            ],
        })
    return tables


def _tables_ttest_independent(r: Dict) -> List[Dict]:
    tables = []

    # Group stats
    gs = r.get("group_stats", [])
    if gs:
        tables.append({
            "title": "Group Statistics",
            "columns": ["Group", "N", "Mean", "Std. Deviation", "SE Mean"],
            "rows": [[g.get("group"), g.get("n"), g.get("mean"), g.get("std"), g.get("se")] for g in gs],
        })

    # Test results
    tables.append({
        "title": "Independent Samples Test",
        "columns": ["t", "df", "Sig. (2-tailed)", "Mean Diff.", "95% CI Lower", "95% CI Upper", "Cohen's d"],
        "rows": [[
            r.get("statistic"), r.get("df"), r.get("pvalue"),
            r.get("mean_diff"), r.get("ci_lower"), r.get("ci_upper"), r.get("cohen_d"),
        ]],
    })

    # Levene's
    if r.get("levene_F") is not None:
        tables.append({
            "title": "Levene's Test for Equality of Variances",
            "columns": ["F", "Sig."],
            "rows": [[r.get("levene_F"), r.get("levene_p")]],
        })

    return tables


def _tables_anova(r: Dict) -> List[Dict]:
    tables = []

    gs = r.get("group_stats", [])
    if gs:
        tables.append({
            "title": "Descriptives",
            "columns": ["Group", "N", "Mean", "Std. Deviation", "SE Mean"],
            "rows": [[g.get("group"), g.get("n"), g.get("mean"), g.get("std"), g.get("se")] for g in gs],
        })

    at = r.get("anova_table")
    if at:
        tables.append({
            "title": "ANOVA",
            "columns": at.get("headers", []),
            "rows": at.get("rows", []),
        })

    # Effect size + Levene
    tables.append({
        "title": "Effect Size",
        "columns": ["Measure", "Value"],
        "rows": [
            ["η² (Eta Squared)", r.get("eta_squared")],
            ["Levene's F", r.get("levene_F")],
            ["Levene's Sig.", r.get("levene_p")],
        ],
    })

    # Post-hoc
    ph = r.get("posthoc_results", [])
    if ph:
        tables.append({
            "title": "Post-Hoc Multiple Comparisons",
            "columns": ["Group 1", "Group 2", "Mean Diff.", "Sig."],
            "rows": [[p.get("group_1"), p.get("group_2"), p.get("mean_diff"),
                       "Yes*" if p.get("reject") else "No"] for p in ph],
        })

    return tables


def _tables_correlation(r: Dict) -> List[Dict]:
    variables = r.get("variables", [])
    r_matrix = r.get("r_matrix", [])
    p_matrix = r.get("p_matrix", [])
    if not variables or not r_matrix:
        return [_safe_rows(r)]

    # Correlation matrix as table
    rows = []
    for i, var in enumerate(variables):
        row = [var]
        for j in range(len(variables)):
            r_val = r_matrix[i][j] if i < len(r_matrix) and j < len(r_matrix[i]) else None
            p_val = p_matrix[i][j] if p_matrix and i < len(p_matrix) and j < len(p_matrix[i]) else None
            cell = f"{r_val:.3f}" if r_val is not None else "—"
            if p_val is not None and p_val < 0.01:
                cell += "**"
            elif p_val is not None and p_val < 0.05:
                cell += "*"
            row.append(cell)
        rows.append(row)

    return [{
        "title": f"Correlations ({r.get('method', 'pearson')})",
        "columns": [""] + variables,
        "rows": rows,
    }]


def _tables_regression(r: Dict) -> List[Dict]:
    tables = [{
        "title": "Model Summary",
        "columns": ["R", "R²", "Adj. R²", "Std. Error", "Durbin-Watson"],
        "rows": [[r.get("r"), r.get("r2"), r.get("adj_r2"), r.get("std_error_estimate"), r.get("durbin_watson")]],
    }]

    at = r.get("anova_table")
    if at:
        tables.append({"title": "ANOVA", "columns": at.get("headers", []), "rows": at.get("rows", [])})

    coeffs = r.get("coefficients", [])
    if coeffs:
        tables.append({
            "title": "Coefficients",
            "columns": ["Variable", "B", "Std. Error", "β", "t", "Sig.", "VIF"],
            "rows": [[
                c.get("variable"), c.get("B"), c.get("std_error"), c.get("beta"),
                c.get("t"), c.get("pvalue"), c.get("vif"),
            ] for c in coeffs],
        })
    return tables


def _tables_logistic(r: Dict) -> List[Dict]:
    tables = [{
        "title": "Model Summary",
        "columns": ["-2 Log Likelihood", "Cox & Snell R²", "Nagelkerke R²"],
        "rows": [[r.get("neg_2LL"), r.get("cox_snell_r2"), r.get("nagelkerke_r2")]],
    }]

    coeffs = r.get("coefficients", [])
    if coeffs:
        tables.append({
            "title": "Variables in the Equation",
            "columns": ["Variable", "B", "SE", "Wald", "df", "Sig.", "Exp(B)"],
            "rows": [[
                c.get("variable"), c.get("B"), c.get("std_error"), c.get("wald"),
                c.get("df"), c.get("pvalue"), c.get("exp_B"),
            ] for c in coeffs],
        })

    ct = r.get("classification_table")
    if ct:
        tables.append({
            "title": "Classification Table",
            "columns": ["TP", "TN", "FP", "FN", "Accuracy %"],
            "rows": [[ct.get("tp"), ct.get("tn"), ct.get("fp"), ct.get("fn"), ct.get("accuracy_pct")]],
        })
    return tables


def _tables_reliability(r: Dict) -> List[Dict]:
    tables = [{
        "title": "Reliability Statistics",
        "columns": ["Cronbach's α", "95% CI Lower", "95% CI Upper", "N Items", "N Cases"],
        "rows": [[r.get("cronbach_alpha"), r.get("cronbach_alpha_ci_lower"),
                   r.get("cronbach_alpha_ci_upper"), r.get("n_items"), r.get("n_cases")]],
    }]

    items = r.get("item_stats", [])
    if items:
        tables.append({
            "title": "Item-Total Statistics",
            "columns": ["Item", "Mean", "Std. Dev", "Corrected Item-Total r", "α if Deleted"],
            "rows": [[i.get("variable"), i.get("mean"), i.get("std"),
                       i.get("item_total_corr"), i.get("alpha_if_deleted")] for i in items],
        })
    return tables


def _tables_factor(r: Dict) -> List[Dict]:
    tables = [{
        "title": "KMO and Bartlett's Test",
        "columns": ["Statistic", "Value"],
        "rows": [
            ["Kaiser-Meyer-Olkin MSA", r.get("kmo")],
            ["Bartlett's χ²", r.get("bartlett_chi2")],
            ["df", r.get("bartlett_df")],
            ["Sig.", r.get("bartlett_p")],
        ],
    }]

    eigenvalues = r.get("eigenvalues", [])
    ev = r.get("explained_variance", [])
    cv = r.get("cumulative_variance", [])
    if eigenvalues:
        tables.append({
            "title": "Total Variance Explained",
            "columns": ["Factor", "Eigenvalue", "% of Variance", "Cumulative %"],
            "rows": [[i + 1, eigenvalues[i], ev[i] if i < len(ev) else None,
                       cv[i] if i < len(cv) else None] for i in range(len(eigenvalues))],
        })

    headers = r.get("headers", [])
    rows = r.get("rows", [])
    if headers and rows:
        rotation = r.get("rotation", "none")
        title = f"Rotated Component Matrix ({rotation})" if rotation != "none" else "Component Matrix"
        tables.append({"title": title, "columns": headers, "rows": rows})

    return tables
