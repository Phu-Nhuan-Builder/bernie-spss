"""
Hypothesis Tests Service
T-tests, ANOVA, Means — pure statistical functions
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def _cohen_d_independent(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Cohen's d for independent samples."""
    n_a, n_b = len(group_a), len(group_b)
    if n_a < 2 or n_b < 2:
        return 0.0
    pooled_std = np.sqrt(
        ((n_a - 1) * np.var(group_a, ddof=1) + (n_b - 1) * np.var(group_b, ddof=1))
        / (n_a + n_b - 2)
    )
    if pooled_std == 0:
        return 0.0
    return float((np.mean(group_a) - np.mean(group_b)) / pooled_std)


def _ci_mean_diff(group_a: np.ndarray, group_b: np.ndarray, alpha: float = 0.05, equal_var: bool = True) -> tuple:
    """95% CI for mean difference."""
    n_a, n_b = len(group_a), len(group_b)
    mean_diff = np.mean(group_a) - np.mean(group_b)
    if equal_var:
        # Pooled SE
        sp2 = ((n_a - 1) * np.var(group_a, ddof=1) + (n_b - 1) * np.var(group_b, ddof=1)) / (n_a + n_b - 2)
        se = np.sqrt(sp2 * (1 / n_a + 1 / n_b))
        df = n_a + n_b - 2
    else:
        # Welch SE
        se = np.sqrt(np.var(group_a, ddof=1) / n_a + np.var(group_b, ddof=1) / n_b)
        # Welch-Satterthwaite df
        v_a = np.var(group_a, ddof=1) / n_a
        v_b = np.var(group_b, ddof=1) / n_b
        df = (v_a + v_b) ** 2 / (v_a ** 2 / (n_a - 1) + v_b ** 2 / (n_b - 1))

    t_crit = stats.t.ppf(1 - alpha / 2, df)
    return float(mean_diff - t_crit * se), float(mean_diff + t_crit * se)


def independent_ttest(
    df: pd.DataFrame, group_var: str, test_var: str,
    equal_var: bool = True, alternative: str = "two-sided"
) -> dict:
    """
    Independent samples t-test with Levene's test and Cohen's d.
    Matches SPSS Independent-Samples T Test output.
    """
    groups = df[group_var].dropna().unique()
    if len(groups) < 2:
        raise ValueError(f"Group variable '{group_var}' must have at least 2 distinct groups")

    group_data = []
    group_stats = []
    for g in sorted(groups):
        arr = df.loc[df[group_var] == g, test_var].dropna().to_numpy(dtype=float)
        if len(arr) < 2:
            raise ValueError(f"Group {g} has fewer than 2 observations")
        group_data.append(arr)
        group_stats.append({
            "group": g.item() if hasattr(g, 'item') else g,
            "n": int(len(arr)),
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr, ddof=1)), 4),
            "se": round(float(np.std(arr, ddof=1) / np.sqrt(len(arr))), 4),
        })

    a, b = group_data[0], group_data[1]

    # Levene's test (both center='mean' classic and center='median' Brown-Forsythe)
    levene_F, levene_p = stats.levene(a, b, center="mean")
    bf_F, bf_p = stats.levene(a, b, center="median")

    # T-test
    t_stat, p_val = stats.ttest_ind(a, b, equal_var=equal_var, alternative=alternative)
    df_val = len(a) + len(b) - 2 if equal_var else None
    if not equal_var:
        # Welch-Satterthwaite df
        v_a = np.var(a, ddof=1) / len(a)
        v_b = np.var(b, ddof=1) / len(b)
        df_val = (v_a + v_b) ** 2 / (v_a ** 2 / (len(a) - 1) + v_b ** 2 / (len(b) - 1))

    # Effect size
    cohen_d = _cohen_d_independent(a, b)

    # 95% CI
    ci_lower, ci_upper = _ci_mean_diff(a, b, equal_var=equal_var)
    mean_diff = float(np.mean(a) - np.mean(b))

    result = {
        "test_type": "independent",
        "statistic": round(float(t_stat), 4),
        "df": round(float(df_val), 4),
        "pvalue": round(float(p_val), 4),
        "mean_diff": round(mean_diff, 4),
        "cohen_d": round(cohen_d, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "levene_F": round(float(levene_F), 4),
        "levene_p": round(float(levene_p), 4),
        "brown_forsythe_F": round(float(bf_F), 4),
        "brown_forsythe_p": round(float(bf_p), 4),
        "group_stats": group_stats,
        "equal_var": equal_var,
        "alternative": alternative,
        "headers": ["", "Levene's Test F", "Levene's p", "t", "df", "Sig. (2-tailed)", "Mean Diff.", "95% CI Lower", "95% CI Upper", "Cohen's d"],
        "rows": [
            ["Equal variances assumed" if equal_var else "Equal variances not assumed",
             round(float(levene_F), 4), round(float(levene_p), 4),
             round(float(t_stat), 4), round(float(df_val), 4),
             round(float(p_val), 4), round(mean_diff, 4), round(ci_lower, 4), round(ci_upper, 4), round(cohen_d, 4)]
        ],
    }
    return result


def paired_ttest(df: pd.DataFrame, var1: str, var2: str) -> dict:
    """
    Paired samples t-test with effect size (Cohen's dz).
    """
    paired = df[[var1, var2]].dropna()
    a = paired[var1].to_numpy(dtype=float)
    b = paired[var2].to_numpy(dtype=float)
    n = len(a)

    if n < 2:
        raise ValueError("Need at least 2 paired observations")

    diff = a - b
    t_stat, p_val = stats.ttest_rel(a, b)
    df_val = n - 1
    mean_diff = float(np.mean(diff))
    std_diff = float(np.std(diff, ddof=1))
    se_diff = std_diff / np.sqrt(n)

    # Cohen's dz (SPSS uses dz for paired)
    cohen_dz = mean_diff / std_diff if std_diff > 0 else 0.0

    # 95% CI
    t_crit = stats.t.ppf(0.975, df_val)
    ci_lower = mean_diff - t_crit * se_diff
    ci_upper = mean_diff + t_crit * se_diff

    # Correlation between vars
    r, r_p = stats.pearsonr(a, b)

    return {
        "test_type": "paired",
        "var1": var1,
        "var2": var2,
        "n": n,
        "mean_diff": round(mean_diff, 4),
        "std_diff": round(std_diff, 4),
        "se_diff": round(se_diff, 4),
        "statistic": round(float(t_stat), 4),
        "df": df_val,
        "pvalue": round(float(p_val), 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "cohen_dz": round(cohen_dz, 4),
        "correlation": round(float(r), 4),
        "correlation_p": round(float(r_p), 4),
        "headers": ["Pair", "Mean", "Std Dev", "SE Mean", "t", "df", "Sig. (2-tailed)", "Cohen's dz"],
        "rows": [[f"{var1} – {var2}", round(mean_diff, 4), round(std_diff, 4), round(se_diff, 4), round(float(t_stat), 4), df_val, round(float(p_val), 4), round(cohen_dz, 4)]],
    }


def one_sample_ttest(df: pd.DataFrame, variable: str, test_value: float = 0.0) -> dict:
    """
    One-sample t-test against a known population mean.
    Matches SPSS One-Sample T Test output.
    """
    series = df[variable].dropna().to_numpy(dtype=float)
    n = len(series)
    if n < 2:
        raise ValueError("Need at least 2 observations")

    mean = float(np.mean(series))
    std = float(np.std(series, ddof=1))
    se = std / np.sqrt(n)
    t_stat, p_val = stats.ttest_1samp(series, test_value)
    df_val = n - 1
    mean_diff = mean - test_value

    # 95% CI of the difference
    t_crit = stats.t.ppf(0.975, df_val)
    ci_lower = mean_diff - t_crit * se
    ci_upper = mean_diff + t_crit * se

    # Cohen's d
    cohen_d = mean_diff / std if std > 0 else 0.0

    return {
        "test_type": "one_sample",
        "variable": variable,
        "test_value": test_value,
        "n": n,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "se": round(se, 4),
        "statistic": round(float(t_stat), 4),
        "df": df_val,
        "pvalue": round(float(p_val), 4),
        "mean_diff": round(mean_diff, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "cohen_d": round(cohen_d, 4),
        "headers": ["Variable", "N", "Mean", "Std Dev", "SE Mean", "t", "df", "Sig.", "Mean Diff.", "95% CI Lower", "95% CI Upper"],
        "rows": [[variable, n, round(mean, 4), round(std, 4), round(se, 4), round(float(t_stat), 4), df_val, round(float(p_val), 4), round(mean_diff, 4), round(ci_lower, 4), round(ci_upper, 4)]],
    }


def _scheffe_test(groups_data: List[np.ndarray], group_labels: List[Any], ms_within: float, df_within: int) -> List[dict]:
    """
    Scheffé post-hoc test.
    Critical value: (k-1) × F_crit(k-1, df_within)
    """
    k = len(groups_data)
    f_crit = stats.f.ppf(0.95, k - 1, df_within)
    results = []
    for i in range(k):
        for j in range(i + 1, k):
            a, b = groups_data[i], groups_data[j]
            diff = float(np.mean(a) - np.mean(b))
            se = float(np.sqrt(ms_within * (1 / len(a) + 1 / len(b))))
            f_val = (diff ** 2) / (ms_within * (1 / len(a) + 1 / len(b))) if se > 0 else 0
            critical_diff = float(np.sqrt((k - 1) * f_crit) * se)
            p_val = float(1 - stats.f.cdf(f_val / (k - 1), k - 1, df_within)) if f_val > 0 else 1.0
            results.append({
                "group_1": group_labels[i],
                "group_2": group_labels[j],
                "mean_diff": round(diff, 4),
                "se": round(se, 4),
                "p_value": round(min(p_val, 1.0), 4),
                "critical_diff": round(critical_diff, 4),
                "significant": abs(diff) > critical_diff,
            })
    return results


def one_way_anova(
    df: pd.DataFrame, group_var: str, dep_var: str, posthoc: str = "tukey"
) -> dict:
    """
    One-way ANOVA with Levene's test and post-hoc comparisons.
    Matches SPSS One-Way ANOVA output.
    """
    groups_df = df[[group_var, dep_var]].dropna()
    group_labels = sorted(groups_df[group_var].unique())
    # Convert numpy types to native Python for JSON serialization
    group_labels = [x.item() if hasattr(x, 'item') else x for x in group_labels]
    groups_data = [groups_df.loc[groups_df[group_var] == g, dep_var].to_numpy(dtype=float) for g in group_labels]

    if any(len(g) < 2 for g in groups_data):
        raise ValueError("Each group must have at least 2 observations")

    # ANOVA
    f_stat, p_val = stats.f_oneway(*groups_data)
    n_total = sum(len(g) for g in groups_data)
    k = len(groups_data)
    grand_mean = np.mean(np.concatenate(groups_data))

    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups_data)
    ss_within = sum(np.sum((g - np.mean(g)) ** 2) for g in groups_data)
    ss_total = ss_between + ss_within
    df_between = k - 1
    df_within = n_total - k
    ms_between = ss_between / df_between if df_between > 0 else 0
    ms_within = ss_within / df_within if df_within > 0 else 0
    eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

    # Levene's test
    levene_F, levene_p = stats.levene(*groups_data, center="mean")

    # Group stats
    group_stats = []
    for lbl, arr in zip(group_labels, groups_data):
        group_stats.append({
            "group": lbl.item() if hasattr(lbl, 'item') else lbl,
            "n": int(len(arr)),
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr, ddof=1)), 4),
            "se": round(float(np.std(arr, ddof=1) / np.sqrt(len(arr))), 4),
        })

    # Post-hoc
    posthoc_results = None
    try:
        if posthoc == "tukey":
            from statsmodels.stats.multicomp import pairwise_tukeyhsd
            endog = np.concatenate(groups_data)
            groups_col = np.concatenate([np.full(len(g), lbl) for g, lbl in zip(groups_data, group_labels)])
            tukey = pairwise_tukeyhsd(endog, groups_col, alpha=0.05)
            posthoc_results = []
            for row in tukey.summary().data[1:]:
                posthoc_results.append({
                    "group_1": row[0].item() if hasattr(row[0], 'item') else row[0],
                    "group_2": row[1].item() if hasattr(row[1], 'item') else row[1],
                    "mean_diff": round(float(row[2]), 4),
                    "p_value": round(float(row[3]), 4),
                    "ci_lower": round(float(row[4]), 4),
                    "ci_upper": round(float(row[5]), 4),
                    "reject": bool(row[6]),
                })
        elif posthoc == "bonferroni":
            from statsmodels.stats.multicomp import MultiComparison
            endog = np.concatenate(groups_data)
            groups_col = np.concatenate([np.full(len(g), lbl) for g, lbl in zip(groups_data, group_labels)])
            mc = MultiComparison(endog, groups_col)
            result_mc = mc.allpairtest(stats.ttest_ind, method="bonf")
            posthoc_results = []
            for row in result_mc[0].data[1:]:
                posthoc_results.append({
                    "group_1": row[0], "group_2": row[1],
                    "p_value": round(float(row[2]), 4) if row[2] is not None else None,
                    "reject": bool(row[3]) if row[3] is not None else False,
                })
        elif posthoc == "scheffe":
            posthoc_results = _scheffe_test(groups_data, group_labels, ms_within, df_within)
    except Exception as e:
        logger.warning(f"Post-hoc test failed: {e}")
        posthoc_results = []

    return {
        "dep_var": dep_var,
        "group_var": group_var,
        "f_statistic": round(float(f_stat), 4),
        "df_between": df_between,
        "df_within": df_within,
        "p_value": round(float(p_val), 4),
        "eta_squared": round(float(eta_squared), 4),
        "levene_F": round(float(levene_F), 4),
        "levene_p": round(float(levene_p), 4),
        "group_stats": group_stats,
        "posthoc_results": posthoc_results,
        "anova_table": {
            "headers": ["Source", "SS", "df", "MS", "F", "Sig."],
            "rows": [
                ["Between Groups", round(ss_between, 4), df_between, round(ms_between, 4), round(float(f_stat), 4), round(float(p_val), 4)],
                ["Within Groups", round(ss_within, 4), df_within, round(ms_within, 4), "", ""],
                ["Total", round(ss_total, 4), n_total - 1, "", "", ""],
            ],
        },
        "headers": ["Source", "SS", "df", "MS", "F", "Sig."],
        "rows": [
            ["Between Groups", round(ss_between, 4), df_between, round(ms_between, 4), round(float(f_stat), 4), round(float(p_val), 4)],
            ["Within Groups", round(ss_within, 4), df_within, round(ms_within, 4), "", ""],
            ["Total", round(ss_total, 4), n_total - 1, "", "", ""],
        ],
    }


def compute_means(df: pd.DataFrame, dep_var: str, factor_var: str) -> dict:
    """
    Compute group means table with ANOVA (Means procedure).
    """
    paired = df[[dep_var, factor_var]].dropna()
    groups = sorted(paired[factor_var].unique())

    group_means = []
    for g in groups:
        arr = paired.loc[paired[factor_var] == g, dep_var].to_numpy(dtype=float)
        group_means.append({
            "group": g,
            "n": int(len(arr)),
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr, ddof=1)), 4) if len(arr) > 1 else 0.0,
            "se": round(float(np.std(arr, ddof=1) / np.sqrt(len(arr))), 4) if len(arr) > 1 else 0.0,
            "min": round(float(np.min(arr)), 4),
            "max": round(float(np.max(arr)), 4),
        })

    # Overall stats
    all_arr = paired[dep_var].to_numpy(dtype=float)
    group_means.append({
        "group": "Total",
        "n": int(len(all_arr)),
        "mean": round(float(np.mean(all_arr)), 4),
        "std": round(float(np.std(all_arr, ddof=1)), 4),
        "se": round(float(np.std(all_arr, ddof=1) / np.sqrt(len(all_arr))), 4),
        "min": round(float(np.min(all_arr)), 4),
        "max": round(float(np.max(all_arr)), 4),
    })

    return {
        "dep_var": dep_var,
        "factor_var": factor_var,
        "group_means": group_means,
        "headers": [factor_var, "N", "Mean", "Std Dev", "SE Mean", "Min", "Max"],
        "rows": [[g["group"], g["n"], g["mean"], g["std"], g["se"], g["min"], g["max"]] for g in group_means],
    }
