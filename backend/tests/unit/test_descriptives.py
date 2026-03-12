"""
Unit tests for descriptive statistics service.
Tests against known values.
"""
import pytest
import numpy as np
import pandas as pd

from app.domain.services.descriptives import (
    compute_frequencies, compute_descriptives, compute_crosstabs,
    compute_explore, spss_boxplot_stats
)


@pytest.fixture
def sample_df():
    """50-row dataset with known statistical properties."""
    np.random.seed(42)
    return pd.DataFrame({
        "age": [22, 25, 21, 28, 23, 30, 24, 26, 22, 29,
                21, 27, 23, 25, 22, 28, 24, 26, 23, 30,
                22, 25, 21, 28, 23, 30, 24, 26, 22, 29,
                21, 27, 23, 25, 22, 28, 24, 26, 23, 30,
                22, 25, 21, 28, 23, 30, 24, 26, 22, 29],
        "score": [78.5, 82.3, 65.4, 90.1, 71.2, 88.7, 79.8, 84.5, 68.3, 92.1,
                  75.6, 81.4, 70.2, 86.3, 73.8, 89.5, 77.1, 83.6, 69.4, 91.2,
                  76.8, 82.9, 64.7, 90.5, 72.3, 87.4, 78.6, 84.1, 67.9, 93.2,
                  74.5, 80.8, 71.7, 85.6, 72.4, 88.9, 76.2, 83.0, 70.8, 90.7,
                  75.3, 81.6, 63.9, 91.8, 73.1, 86.5, 79.4, 84.8, 68.7, 92.4],
        "gender": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2] * 5,
        "group": [1, 1, 2, 1, 2, 1, 2, 1, 2, 1] * 5,
    })


class TestFrequencies:
    def test_basic_frequencies(self, sample_df):
        result = compute_frequencies(sample_df, "gender")
        assert "rows" in result
        assert result["n_total"] == 50
        assert result["n_missing"] == 0
        # Gender has 2 unique values (1 and 2)
        assert len([r for r in result["row_details"] if r["value"] != "Missing"]) == 2

    def test_percentages_sum_to_100(self, sample_df):
        result = compute_frequencies(sample_df, "gender")
        total_pct = sum(r["percent"] for r in result["row_details"] if r["value"] != "Missing")
        assert abs(total_pct - 100.0) < 0.5  # allow rounding

    def test_with_missing_values(self, sample_df):
        df = sample_df.copy()
        df.loc[0, "gender"] = np.nan
        result = compute_frequencies(df, "gender")
        assert result["n_missing"] == 1
        assert result["n_valid"] == 49

    def test_value_labels_applied(self, sample_df):
        vl = {"1": "Male", "2": "Female"}
        result = compute_frequencies(sample_df, "gender", vl)
        labels = [r["label"] for r in result["row_details"]]
        assert "Male" in labels
        assert "Female" in labels


class TestDescriptives:
    def test_basic_stats(self, sample_df):
        result = compute_descriptives(sample_df, ["age", "score"])
        assert len(result["rows"]) == 2

        age_row = next(r for r in result["rows"] if r["variable"] == "age")
        assert age_row["n"] == 50
        assert 23 < age_row["mean"] < 27  # age mean is around 24-25
        assert age_row["minimum"] == 21
        assert age_row["maximum"] == 30

    def test_score_mean(self, sample_df):
        result = compute_descriptives(sample_df, ["score"])
        score_row = result["rows"][0]
        # Known mean from sample data
        expected_mean = sum([78.5, 82.3, 65.4, 90.1, 71.2, 88.7, 79.8, 84.5, 68.3, 92.1,
                             75.6, 81.4, 70.2, 86.3, 73.8, 89.5, 77.1, 83.6, 69.4, 91.2,
                             76.8, 82.9, 64.7, 90.5, 72.3, 87.4, 78.6, 84.1, 67.9, 93.2,
                             74.5, 80.8, 71.7, 85.6, 72.4, 88.9, 76.2, 83.0, 70.8, 90.7,
                             75.3, 81.6, 63.9, 91.8, 73.1, 86.5, 79.4, 84.8, 68.7, 92.4]) / 50
        assert abs(score_row["mean"] - expected_mean) < 0.01

    def test_std_dev_positive(self, sample_df):
        result = compute_descriptives(sample_df, ["score"])
        assert result["rows"][0]["std_dev"] > 0

    def test_skewness_kurtosis(self, sample_df):
        result = compute_descriptives(sample_df, ["score"])
        row = result["rows"][0]
        assert row["skewness"] is not None
        assert row["kurtosis"] is not None


class TestCrosstabs:
    def test_basic_crosstab(self, sample_df):
        result = compute_crosstabs(sample_df, "gender", "group")
        assert "chi2" in result
        assert result["chi2"] is not None
        assert result["n"] == 50

    def test_chi2_format(self, sample_df):
        result = compute_crosstabs(sample_df, "gender", "group")
        assert isinstance(result["chi2"], float)
        assert isinstance(result["p_value"], float)
        assert 0 <= result["p_value"] <= 1

    def test_cramers_v_range(self, sample_df):
        result = compute_crosstabs(sample_df, "gender", "group")
        if result["cramers_v"] is not None:
            assert 0 <= result["cramers_v"] <= 1


class TestBoxPlotStats:
    def test_spss_exact_whiskers(self):
        """EXACT whisker logic: actual data points, not fence boundaries."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50]  # 50 is an outlier
        result = spss_boxplot_stats(data)
        assert result["whisker_low"] == 1  # smallest non-outlier
        assert result["whisker_high"] == 10  # largest non-outlier (50 is above fence)
        assert 50 in result["mild_outliers"] or 50 in result["extreme_outliers"]

    def test_normal_data_no_outliers(self):
        """Normal data should have no outliers."""
        data = list(range(1, 21))  # 1 to 20
        result = spss_boxplot_stats(data)
        assert len(result["mild_outliers"]) == 0
        assert len(result["extreme_outliers"]) == 0

    def test_whiskers_are_actual_data_points(self):
        """Critical: whiskers must be actual data points, not fence values."""
        data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 5, 105]
        result = spss_boxplot_stats(data)
        # Verify whiskers are in original data
        assert result["whisker_low"] in data
        assert result["whisker_high"] in data


class TestExplore:
    def test_shapiro_wilk(self, sample_df):
        result = compute_explore(sample_df, "score")
        assert result["shapiro_w"] is not None
        assert 0 <= result["shapiro_w"] <= 1
        assert 0 <= result["shapiro_p"] <= 1

    def test_percentiles(self, sample_df):
        result = compute_explore(sample_df, "score")
        percentiles = result["percentiles"]
        assert "25" in percentiles
        assert "50" in percentiles
        assert "75" in percentiles
        # Verify ordering
        assert percentiles["25"] <= percentiles["50"] <= percentiles["75"]
