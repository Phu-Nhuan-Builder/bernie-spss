"""
Regression & Correlation Service
OLS, Binary Logistic, Pearson/Spearman Correlation
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def spss_qq_data(data: list) -> dict:
    """
    Q-Q plot data using SPSS Blom (1958) plotting position.
    p_i = (i - 3/8) / (n + 1/4)  — NOT scipy default (Filliben)
    """
    arr = np.sort([x for x in data if x is not None and not np.isnan(float(x))])
    n = len(arr)
    if n == 0:
        return {"observed": [], "theoretical": [], "fit_slope": 1.0, "fit_intercept": 0.0}

    i = np.arange(1, n + 1)
    # Blom formula (SPSS default)
    p = (i - 3 / 8) / (n + 1 / 4)
    theoretical = stats.norm.ppf(p)

    # Fitting line from Q1/Q3 of both distributions
    q1_obs, q3_obs = np.percentile(arr, [25, 75])
    q1_th, q3_th = stats.norm.ppf([0.25, 0.75])
    slope = (q3_obs - q1_obs) / (q3_th - q1_th) if (q3_th - q1_th) != 0 else 1.0
    intercept = q1_obs - slope * q1_th

    return {
        "observed": arr.tolist(),
        "theoretical": theoretical.tolist(),
        "fit_slope": float(slope),
        "fit_intercept": float(intercept),
    }


def compute_residuals(y: np.ndarray, X: np.ndarray) -> dict:
    """
    EXACT from RESEARCH.md — compute regression influence statistics.
    Standardized residuals, studentized deleted residuals, leverage, Cook's distance, DFFITS.
    """
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import OLSInfluence

    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()
    influence = OLSInfluence(model)

    return {
        "standardized_residuals": influence.resid_studentized_internal.tolist(),
        "studentized_deleted_residuals": influence.resid_studentized_external.tolist(),
        "leverage": influence.hat_matrix_diag.tolist(),
        "cooks_distance": influence.cooks_distance[0].tolist(),
        "dffits": influence.dffits[0].tolist(),
    }


def pearson_spearman_correlation(
    df: pd.DataFrame, variables: List[str], method: str = "pearson"
) -> dict:
    """
    Bivariate correlation matrix with significance testing.
    Uses pingouin for SPSS-compatible output.
    Matches SPSS Bivariate Correlations output.
    """
    import pingouin as pg

    subset = df[variables].dropna()
    n_vars = len(variables)
    n = len(subset)

    # Build pairwise correlation matrices
    r_matrix = [[None] * n_vars for _ in range(n_vars)]
    p_matrix = [[None] * n_vars for _ in range(n_vars)]
    n_matrix = [[n] * n_vars for _ in range(n_vars)]

    for i in range(n_vars):
        for j in range(n_vars):
            if i == j:
                r_matrix[i][j] = 1.0
                p_matrix[i][j] = None
            else:
                pair = df[[variables[i], variables[j]]].dropna()
                n_pair = len(pair)
                n_matrix[i][j] = n_pair
                if n_pair < 3:
                    r_matrix[i][j] = None
                    p_matrix[i][j] = None
                    continue
                x = pair[variables[i]].to_numpy(dtype=float)
                y = pair[variables[j]].to_numpy(dtype=float)
                if method == "pearson":
                    r, p = stats.pearsonr(x, y)
                else:
                    r, p = stats.spearmanr(x, y)
                r_matrix[i][j] = round(float(r), 4)
                p_matrix[i][j] = round(float(p), 4)

    # Build table output (SPSS-style correlation matrix)
    headers = [""] + variables
    rows = []
    for i, var in enumerate(variables):
        rows.append([var] + [
            f"{r_matrix[i][j]:.3f}" + ("*" if p_matrix[i][j] is not None and p_matrix[i][j] < 0.05 else "")
            + ("*" if p_matrix[i][j] is not None and p_matrix[i][j] < 0.01 else "")
            if r_matrix[i][j] is not None else "1.000"
            for j in range(n_vars)
        ])
        rows.append(["Sig. (2-tailed)"] + [
            f"{p_matrix[i][j]:.3f}" if p_matrix[i][j] is not None else ""
            for j in range(n_vars)
        ])
        rows.append(["N"] + [str(n_matrix[i][j]) for j in range(n_vars)])

    return {
        "method": method,
        "variables": variables,
        "r_matrix": r_matrix,
        "p_matrix": p_matrix,
        "n_matrix": n_matrix,
        "headers": headers,
        "rows": rows,
    }


def ols_regression(
    df: pd.DataFrame, dependent: str, independents: List[str],
    method: str = "enter", include_diagnostics: bool = True
) -> dict:
    """
    OLS Linear Regression with full SPSS-compatible output.
    Includes ANOVA table, coefficients (B, Beta, t, p, 95% CI), VIF, condition indices,
    Durbin-Watson, standardized residuals.
    """
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from statsmodels.stats.stattools import durbin_watson

    # Prepare data
    cols = [dependent] + independents
    data = df[cols].dropna()
    y = data[dependent].to_numpy(dtype=float)
    X = data[independents].to_numpy(dtype=float)
    n = len(y)
    k = len(independents)

    if n < k + 2:
        raise ValueError(f"Insufficient observations ({n}) for {k} predictors")

    # Fit OLS with intercept
    X_const = sm.add_constant(X, has_constant="add")
    model = sm.OLS(y, X_const).fit()

    # R² and fit statistics
    r2 = float(model.rsquared)
    adj_r2 = float(model.rsquared_adj)
    r = float(np.sqrt(r2))
    f_stat = float(model.fvalue)
    f_pvalue = float(model.f_pvalue)
    std_error_est = float(np.sqrt(model.mse_resid))

    # ANOVA table
    ss_regression = float(model.ess)
    ss_residual = float(model.ssr)
    ss_total = ss_regression + ss_residual
    df_regression = int(model.df_model)
    df_residual = int(model.df_resid)
    ms_regression = ss_regression / df_regression if df_regression > 0 else 0
    ms_residual = ss_residual / df_residual if df_residual > 0 else 0

    # Standardized betas
    y_std = np.std(y, ddof=1)
    x_stds = np.std(X, axis=0, ddof=1)
    betas = []
    for i in range(k):
        b = float(model.params[i + 1])  # skip intercept
        beta = b * (x_stds[i] / y_std) if y_std > 0 else 0.0
        betas.append(round(beta, 4))

    # VIF
    vif_values = []
    try:
        X_const_arr = np.asarray(X_const, dtype=float)
        for i in range(X.shape[1]):
            vif_values.append(round(float(variance_inflation_factor(X_const_arr, i + 1)), 4))
    except Exception:
        vif_values = [None] * k

    # Coefficients
    coefficients = []
    for i, var in enumerate(["(Constant)"] + independents):
        idx = i
        b = float(model.params[idx])
        se = float(model.bse[idx])
        t = float(model.tvalues[idx])
        p = float(model.pvalues[idx])
        ci = model.conf_int()
        ci_lower = float(ci[idx][0])
        ci_upper = float(ci[idx][1])
        beta = betas[i - 1] if i > 0 else None
        vif = vif_values[i - 1] if i > 0 else None
        tolerance = (1 / vif) if vif and vif > 0 else None
        coefficients.append({
            "variable": var,
            "B": round(b, 4),
            "std_error": round(se, 4),
            "beta": round(beta, 4) if beta is not None else None,
            "t": round(t, 4),
            "pvalue": round(p, 4),
            "ci_lower": round(ci_lower, 4),
            "ci_upper": round(ci_upper, 4),
            "vif": vif,
            "tolerance": round(tolerance, 4) if tolerance is not None else None,
        })

    # Durbin-Watson
    dw = float(durbin_watson(model.resid))

    # Condition indices (SPSS method: column-normalized SVD including intercept)
    condition_indices = None
    try:
        X_aug = np.column_stack([np.ones(n), X])
        X_scaled = X_aug / np.sqrt((X_aug ** 2).sum(axis=0))
        _, singular_values, _ = np.linalg.svd(X_scaled, full_matrices=False)
        eigenvalues = singular_values ** 2
        condition_indices = [round(float(np.sqrt(eigenvalues[0] / ev)), 4) if ev > 0 else None for ev in eigenvalues]
    except Exception:
        pass

    # Residuals data
    residuals_data = None
    if include_diagnostics:
        try:
            residuals_data = compute_residuals(y, X)
        except Exception as e:
            logger.warning(f"Residuals computation failed: {e}")

    return {
        "dependent": dependent,
        "independents": independents,
        "n": n,
        "r": round(r, 4),
        "r2": round(r2, 4),
        "adj_r2": round(adj_r2, 4),
        "std_error_estimate": round(std_error_est, 4),
        "f_stat": round(f_stat, 4),
        "f_df1": df_regression,
        "f_df2": df_residual,
        "f_pvalue": round(f_pvalue, 4),
        "durbin_watson": round(dw, 4),
        "anova_table": {
            "headers": ["", "SS", "df", "MS", "F", "Sig."],
            "rows": [
                ["Regression", round(ss_regression, 4), df_regression, round(ms_regression, 4), round(f_stat, 4), round(f_pvalue, 4)],
                ["Residual", round(ss_residual, 4), df_residual, round(ms_residual, 4), "", ""],
                ["Total", round(ss_total, 4), df_regression + df_residual, "", "", ""],
            ],
        },
        "coefficients": coefficients,
        "condition_indices": condition_indices,
        "residuals_data": residuals_data,
        "headers": ["Variable", "B", "Std Error", "Beta", "t", "Sig.", "95% CI Lower", "95% CI Upper", "VIF"],
        "rows": [
            [c["variable"], c["B"], c["std_error"], c["beta"] if c["beta"] is not None else "",
             c["t"], c["pvalue"], c["ci_lower"], c["ci_upper"], c["vif"] if c["vif"] is not None else ""]
            for c in coefficients
        ],
    }


def binary_logistic(
    df: pd.DataFrame, dependent: str, independents: List[str]
) -> dict:
    """
    Binary Logistic Regression with full SPSS-compatible output.
    Includes log-odds, Exp(B), Wald chi², p-values, 95% CI, pseudo-R², Hosmer-Lemeshow, classification table.
    """
    import statsmodels.api as sm

    cols = [dependent] + independents
    data = df[cols].dropna()
    y = data[dependent].to_numpy(dtype=float)
    X = data[independents].to_numpy(dtype=float)
    n = len(y)

    X_const = sm.add_constant(X, has_constant="add")
    model = sm.Logit(y, X_const).fit(disp=False)

    # Likelihood statistics
    neg_2LL = float(-2 * model.llf)
    neg_2LL_null = float(-2 * model.llnull)
    chi2_model = neg_2LL_null - neg_2LL

    # Pseudo R²
    cox_snell_r2 = float(1 - np.exp(-chi2_model / n))
    nagelkerke_r2 = float(cox_snell_r2 / (1 - np.exp(neg_2LL_null / n))) if (1 - np.exp(neg_2LL_null / n)) > 0 else 0.0

    # Coefficients
    coefficients = []
    for i, var in enumerate(["(Constant)"] + independents):
        b = float(model.params[i])
        se = float(model.bse[i])
        wald = float((b / se) ** 2) if se > 0 else 0.0
        p = float(model.pvalues[i])
        exp_b = float(np.exp(b))
        ci = model.conf_int()
        ci_lower = float(np.exp(ci[0][i]))
        ci_upper = float(np.exp(ci[1][i]))
        coefficients.append({
            "variable": var,
            "B": round(b, 4),
            "std_error": round(se, 4),
            "wald": round(wald, 4),
            "df": 1,
            "pvalue": round(p, 4),
            "exp_B": round(exp_b, 4),
            "ci_lower": round(ci_lower, 4),
            "ci_upper": round(ci_upper, 4),
        })

    # Hosmer-Lemeshow test
    hl_chi2 = None
    hl_p = None
    try:
        y_pred = model.predict(X_const)
        g = 10  # groups
        sorted_idx = np.argsort(y_pred)
        y_sorted = y[sorted_idx]
        pred_sorted = y_pred[sorted_idx]
        group_size = n // g
        hl_stat = 0.0
        for gi in range(g):
            start = gi * group_size
            end = start + group_size if gi < g - 1 else n
            obs_1 = np.sum(y_sorted[start:end])
            exp_1 = np.sum(pred_sorted[start:end])
            obs_0 = (end - start) - obs_1
            exp_0 = (end - start) - exp_1
            if exp_1 > 0:
                hl_stat += (obs_1 - exp_1) ** 2 / exp_1
            if exp_0 > 0:
                hl_stat += (obs_0 - exp_0) ** 2 / exp_0
        hl_chi2 = round(float(hl_stat), 4)
        hl_p = round(float(1 - stats.chi2.cdf(hl_stat, g - 2)), 4)
    except Exception as e:
        logger.warning(f"Hosmer-Lemeshow failed: {e}")

    # Classification table
    classification_table = None
    try:
        y_pred_binary = (model.predict(X_const) >= 0.5).astype(int)
        tp = int(np.sum((y == 1) & (y_pred_binary == 1)))
        tn = int(np.sum((y == 0) & (y_pred_binary == 0)))
        fp = int(np.sum((y == 0) & (y_pred_binary == 1)))
        fn = int(np.sum((y == 1) & (y_pred_binary == 0)))
        accuracy = round((tp + tn) / n * 100, 1) if n > 0 else 0.0
        classification_table = {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "accuracy_pct": accuracy}
    except Exception:
        pass

    return {
        "dependent": dependent,
        "independents": independents,
        "n": n,
        "neg_2LL": round(neg_2LL, 4),
        "cox_snell_r2": round(cox_snell_r2, 4),
        "nagelkerke_r2": round(nagelkerke_r2, 4),
        "hosmer_lemeshow_chi2": hl_chi2,
        "hosmer_lemeshow_p": hl_p,
        "coefficients": coefficients,
        "classification_table": classification_table,
        "headers": ["Variable", "B", "Std Error", "Wald", "df", "Sig.", "Exp(B)", "95% CI Lower", "95% CI Upper"],
        "rows": [[c["variable"], c["B"], c["std_error"], c["wald"], c["df"], c["pvalue"], c["exp_B"], c["ci_lower"], c["ci_upper"]] for c in coefficients],
    }
