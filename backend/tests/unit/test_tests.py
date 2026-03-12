"""
Unit tests for hypothesis tests service.
Tests against scipy reference values.
"""
import pytest
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from app.domain.services.tests import (
    independent_ttest, paired_ttest, one_sample_ttest, one_way_anova
)


@pytest.fixture
def two_group_df():
    """DataFrame with two groups for t-test."""
    np.random.seed(42)
    group_a = np.random.normal(75, 10, 25)
    group_b = np.random.normal(80, 10, 25)
    data = pd.DataFrame({
        "score": np.concatenate([group_a, group_b]),
        "group": ["A"] * 25 + ["B"] * 25,
    })
    return data


@pytest.fixture
def three_group_df():
    """DataFrame with three groups for ANOVA."""
    np.random.seed(42)
    return pd.DataFrame({
        "score": [78, 82, 65, 90, 71, 88, 79, 84, 68, 92,
                  75, 81, 70, 86, 73, 89, 77, 83, 69, 91,
                  60, 65, 58, 70, 62, 67, 63, 68, 55, 72],
        "group": ["A"] * 10 + ["B"] * 10 + ["C"] * 10,
    })


class TestIndependentTTest:
    def test_matches_scipy(self, two_group_df):
        """t-statistic and p-value must match scipy reference."""
        result = independent_ttest(two_group_df, "group", "score")

        group_a = two_group_df.loc[two_group_df["group"] == "A", "score"].values
        group_b = two_group_df.loc[two_group_df["group"] == "B", "score"].values
        ref_t, ref_p = scipy_stats.ttest_ind(group_a, group_b, equal_var=True)

        assert abs(result["statistic"] - float(ref_t)) < 0.01
        assert abs(result["pvalue"] - float(ref_p)) < 0.01

    def test_levene_test_included(self, two_group_df):
        result = independent_ttest(two_group_df, "group", "score")
        assert "levene_F" in result
        assert result["levene_F"] is not None
        assert result["levene_p"] is not None

    def test_cohen_d_computed(self, two_group_df):
        result = independent_ttest(two_group_df, "group", "score")
        assert "cohen_d" in result
        # Cohen's d for ~5 point difference with ~10 SD should be ~0.5
        assert abs(result["cohen_d"]) < 2.0  # reasonable range

    def test_ci_bounds(self, two_group_df):
        result = independent_ttest(two_group_df, "group", "score")
        assert result["ci_lower"] < result["ci_upper"]

    def test_group_stats(self, two_group_df):
        result = independent_ttest(two_group_df, "group", "score")
        assert len(result["group_stats"]) == 2
        for gs in result["group_stats"]:
            assert gs["n"] == 25
            assert gs["mean"] > 0
            assert gs["std"] > 0


class TestPairedTTest:
    def test_matches_scipy(self):
        """Paired t-test must match scipy reference."""
        np.random.seed(42)
        df = pd.DataFrame({
            "pre": np.random.normal(70, 10, 30),
            "post": np.random.normal(75, 10, 30),
        })
        result = paired_ttest(df, "pre", "post")
        ref_t, ref_p = scipy_stats.ttest_rel(df["pre"].values, df["post"].values)
        assert abs(result["statistic"] - float(ref_t)) < 0.01
        assert abs(result["pvalue"] - float(ref_p)) < 0.01

    def test_cohen_dz(self):
        """Cohen's dz for paired data."""
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 3, 4, 5, 6]})
        result = paired_ttest(df, "a", "b")
        # Difference is always 1, std_diff = 0 → dz depends on data
        assert result["cohen_dz"] is not None


class TestOneSampleTTest:
    def test_matches_scipy(self):
        """One-sample t-test against known population mean."""
        np.random.seed(42)
        data = np.random.normal(100, 15, 50)
        df = pd.DataFrame({"iq": data})
        result = one_sample_ttest(df, "iq", test_value=100)
        ref_t, ref_p = scipy_stats.ttest_1samp(data, 100)
        assert abs(result["statistic"] - float(ref_t)) < 0.01
        assert abs(result["pvalue"] - float(ref_p)) < 0.01


class TestOneWayANOVA:
    def test_matches_scipy(self, three_group_df):
        """F-statistic and p-value must match scipy reference."""
        result = one_way_anova(three_group_df, "group", "score")

        groups = [
            three_group_df.loc[three_group_df["group"] == g, "score"].values
            for g in ["A", "B", "C"]
        ]
        ref_f, ref_p = scipy_stats.f_oneway(*groups)

        assert abs(result["f_statistic"] - float(ref_f)) < 0.01
        assert abs(result["p_value"] - float(ref_p)) < 0.01

    def test_eta_squared_range(self, three_group_df):
        result = one_way_anova(three_group_df, "group", "score")
        assert 0 <= result["eta_squared"] <= 1

    def test_anova_table_structure(self, three_group_df):
        result = one_way_anova(three_group_df, "group", "score")
        assert "anova_table" in result
        assert len(result["anova_table"]["rows"]) == 3  # Between, Within, Total

    def test_tukey_posthoc(self, three_group_df):
        result = one_way_anova(three_group_df, "group", "score", posthoc="tukey")
        assert result["posthoc_results"] is not None
        assert len(result["posthoc_results"]) == 3  # C(3,2) = 3 pairs
