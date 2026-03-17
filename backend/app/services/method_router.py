"""
Method Router — Deterministic mapping from intent → statistical method.
This is the RULE-BASED layer that ensures statistical correctness.
LLM decides WHAT to do; this module decides HOW to do it correctly.
"""
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def route_method(
    intent: Dict[str, Any],
    schema: Dict[str, Any],
    df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Given a parsed intent and schema, determine the exact statistical method
    and its parameters. Returns an execution plan.

    Returns:
        {
            "method": str,          # e.g., "independent_ttest"
            "params": dict,         # method-specific parameters
            "description": str,     # human-readable description
            "warnings": [str],      # any data quality warnings
        }
    """
    intent_type = intent.get("intent", "describe")
    variables = intent.get("variables", {})
    numeric_vars = schema.get("numeric_vars", [])
    categorical_vars = schema.get("categorical_vars", [])

    warnings = []

    # ── COMPARE GROUPS ─────────────────────────────────────────────────────
    if intent_type == "compare_groups":
        return _route_comparison(variables, numeric_vars, categorical_vars, df, warnings)

    # ── FIND RELATIONSHIP ──────────────────────────────────────────────────
    if intent_type == "find_relationship":
        return _route_relationship(variables, numeric_vars, df, warnings)

    # ── PREDICT ────────────────────────────────────────────────────────────
    if intent_type == "predict":
        return _route_prediction(variables, numeric_vars, df, warnings)

    # ── DESCRIBE ───────────────────────────────────────────────────────────
    if intent_type == "describe":
        target_vars = numeric_vars[:10] if numeric_vars else list(df.columns[:10])
        return {
            "method": "descriptives",
            "params": {"variables": target_vars},
            "description": f"Compute descriptive statistics for {len(target_vars)} variables",
            "warnings": warnings,
        }

    # ── TEST NORMALITY ─────────────────────────────────────────────────────
    if intent_type == "test_normality":
        target = variables.get("dependent") or (numeric_vars[0] if numeric_vars else None)
        if not target:
            return _error_plan("No numeric variable available for normality test")
        return {
            "method": "explore",
            "params": {"variable": target},
            "description": f"Normality test (Shapiro-Wilk) for '{target}'",
            "warnings": warnings,
        }

    # ── CROSSTAB ───────────────────────────────────────────────────────────
    if intent_type == "crosstab":
        cat_vars = categorical_vars[:2] if len(categorical_vars) >= 2 else []
        if len(cat_vars) < 2:
            return _error_plan("Need at least 2 categorical variables for cross-tabulation")
        return {
            "method": "crosstabs",
            "params": {"row_var": cat_vars[0], "col_var": cat_vars[1]},
            "description": f"Cross-tabulation: '{cat_vars[0]}' × '{cat_vars[1]}' with χ² test",
            "warnings": warnings,
        }

    # ── RELIABILITY ────────────────────────────────────────────────────────
    if intent_type == "reliability":
        items = variables.get("independent") or numeric_vars[:10]
        if len(items) < 2:
            return _error_plan("Need at least 2 numeric variables for reliability analysis")
        return {
            "method": "reliability",
            "params": {"variables": items},
            "description": f"Cronbach's alpha for {len(items)} items",
            "warnings": warnings,
        }

    # ── FACTOR ANALYSIS ────────────────────────────────────────────────────
    if intent_type == "factor_analysis":
        items = variables.get("independent") or numeric_vars[:15]
        if len(items) < 3:
            return _error_plan("Need at least 3 numeric variables for factor analysis")
        n_factors = min(3, len(items) // 2)
        return {
            "method": "factor_analysis",
            "params": {"variables": items, "n_factors": n_factors, "extraction": "principal", "rotation": "varimax"},
            "description": f"Exploratory Factor Analysis: {len(items)} items → {n_factors} factors",
            "warnings": warnings,
        }

    return _error_plan(f"Unsupported intent: {intent_type}")


def _route_comparison(variables, numeric_vars, categorical_vars, df, warnings):
    """Route compare_groups intent to correct test."""
    dep = variables.get("dependent")
    group_var = variables.get("group_var")
    indep = variables.get("independent") or []

    # Auto-select if not specified
    if not dep and numeric_vars:
        dep = numeric_vars[0]
        warnings.append(f"Auto-selected dependent variable: '{dep}'")
    if not group_var and categorical_vars:
        group_var = categorical_vars[0]
        warnings.append(f"Auto-selected grouping variable: '{group_var}'")

    if not dep or not group_var:
        return _error_plan("Need a numeric dependent variable and a categorical grouping variable for comparison")

    # Check if group_var exists in df
    if group_var not in df.columns:
        return _error_plan(f"Grouping variable '{group_var}' not found in dataset")

    # Count groups and check min observations per group
    n_groups = df[group_var].nunique()
    min_obs = df.groupby(group_var).size().min()

    # If groups are too small for statistical tests → descriptive comparison
    if min_obs < 2:
        # Build comparison variables list (dep + any extras from independent)
        compare_vars = [dep]
        for v in indep:
            if v in df.columns and v not in compare_vars:
                compare_vars.append(v)
        # Add more numeric vars if we have few
        if len(compare_vars) < 3:
            for v in numeric_vars:
                if v not in compare_vars:
                    compare_vars.append(v)
                if len(compare_vars) >= 6:
                    break

        warnings.append(f"Groups have <2 observations each — using descriptive comparison instead of statistical test")
        return {
            "method": "descriptives",
            "params": {"variables": compare_vars, "group_var": group_var},
            "description": f"Descriptive comparison of {len(compare_vars)} variables by '{group_var}'",
            "warnings": warnings,
        }

    if n_groups == 2:
        return {
            "method": "independent_ttest",
            "params": {"test_var": dep, "group_var": group_var, "equal_var": True},
            "description": f"Independent samples t-test: '{dep}' by '{group_var}' (2 groups)",
            "warnings": warnings,
        }
    elif n_groups > 2:
        return {
            "method": "one_way_anova",
            "params": {"dep_var": dep, "group_var": group_var, "posthoc": "tukey"},
            "description": f"One-way ANOVA: '{dep}' by '{group_var}' ({n_groups} groups) with Tukey HSD",
            "warnings": warnings,
        }
    else:
        return _error_plan(f"Grouping variable '{group_var}' has only {n_groups} group(s)")


def _route_relationship(variables, numeric_vars, df, warnings):
    """Route find_relationship intent to correlation."""
    indep = variables.get("independent") or []
    if len(indep) < 2:
        # Use first N numeric vars
        indep = numeric_vars[:5]
        if len(indep) < 2:
            return _error_plan("Need at least 2 numeric variables for correlation")
        warnings.append(f"Auto-selected variables: {', '.join(indep)}")

    return {
        "method": "correlation",
        "params": {"variables": indep, "method": "pearson"},
        "description": f"Pearson correlation matrix: {len(indep)} variables",
        "warnings": warnings,
    }


def _route_prediction(variables, numeric_vars, df, warnings):
    """Route predict intent to regression."""
    dep = variables.get("dependent")
    indep = variables.get("independent") or []

    if not dep:
        if len(numeric_vars) >= 2:
            dep = numeric_vars[-1]  # last numeric = likely DV
            warnings.append(f"Auto-selected dependent variable: '{dep}'")
        else:
            return _error_plan("Need a dependent variable for regression")

    if not indep:
        indep = [v for v in numeric_vars if v != dep][:5]
        if not indep:
            return _error_plan("Need at least 1 independent variable for regression")
        warnings.append(f"Auto-selected independent variables: {', '.join(indep)}")

    # Check if DV is binary → logistic
    if dep in df.columns:
        unique_vals = df[dep].dropna().nunique()
        if unique_vals == 2:
            return {
                "method": "binary_logistic",
                "params": {"dependent": dep, "independents": indep},
                "description": f"Binary logistic regression: '{dep}' ← {', '.join(indep)}",
                "warnings": warnings,
            }

    return {
        "method": "ols_regression",
        "params": {"dependent": dep, "independents": indep},
        "description": f"OLS linear regression: '{dep}' ← {', '.join(indep)}",
        "warnings": warnings,
    }


def _error_plan(message: str) -> Dict[str, Any]:
    """Return an error execution plan."""
    return {
        "method": "error",
        "params": {},
        "description": message,
        "warnings": [message],
    }


def plan_auto_analysis(schema: Dict[str, Any], df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Generate a full analysis plan for "Analyze for me" mode.
    Returns a list of execution plans covering the key analyses.
    """
    numeric = schema.get("numeric_vars", [])
    categorical = schema.get("categorical_vars", [])
    plans = []

    # 1. Descriptives for all numeric vars
    if numeric:
        plans.append({
            "method": "descriptives",
            "params": {"variables": numeric[:10]},
            "description": f"Descriptive statistics for {min(len(numeric), 10)} variables",
            "warnings": [],
        })

    # 2. Frequency tables for categorical vars
    for cat in categorical[:3]:
        plans.append({
            "method": "frequencies",
            "params": {"variable": cat},
            "description": f"Frequency table for '{cat}'",
            "warnings": [],
        })

    # 3. Correlation matrix if 2+ numeric
    if len(numeric) >= 2:
        plans.append({
            "method": "correlation",
            "params": {"variables": numeric[:6], "method": "pearson"},
            "description": f"Correlation matrix for {min(len(numeric), 6)} numeric variables",
            "warnings": [],
        })

    # 4. Group comparison if we have numeric + categorical
    if numeric and categorical:
        dep = numeric[0]
        grp = categorical[0]
        n_groups = df[grp].nunique()
        if n_groups == 2:
            plans.append({
                "method": "independent_ttest",
                "params": {"test_var": dep, "group_var": grp, "equal_var": True},
                "description": f"Independent t-test: '{dep}' by '{grp}'",
                "warnings": [],
            })
        elif n_groups > 2:
            plans.append({
                "method": "one_way_anova",
                "params": {"dep_var": dep, "group_var": grp, "posthoc": "tukey"},
                "description": f"One-way ANOVA: '{dep}' by '{grp}'",
                "warnings": [],
            })

    # 5. Regression if 3+ numeric
    if len(numeric) >= 3:
        dep = numeric[-1]
        indep = [v for v in numeric if v != dep][:4]
        plans.append({
            "method": "ols_regression",
            "params": {"dependent": dep, "independents": indep},
            "description": f"OLS regression: '{dep}' ← {', '.join(indep)}",
            "warnings": [],
        })

    # 6. Normality for first numeric
    if numeric:
        plans.append({
            "method": "explore",
            "params": {"variable": numeric[0]},
            "description": f"Normality test for '{numeric[0]}'",
            "warnings": [],
        })

    return plans
