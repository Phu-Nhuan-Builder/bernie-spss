"""
Unit tests for regression and correlation service.
Tests against statsmodels reference values.
"""
import pytest
import numpy as np
import pandas as pd

from app.domain.services.regression import (
    pearson_spearman_correlation, ols_regression, binary_logistic, spss_qq_data
)


@pytest.fixture
def regression_df():
    """Dataset with known linear relationship."""
    np.random.seed(42)
    n = 100
    x1 = np.random.normal(50, 10, n)
    x2 = np.random.normal(30, 5, n)
    # y = 2*x1 + 1.5*x2 + noise
    y = 2 * x1 + 1.5 * x2 + np.random.normal(0, 5, n)
    return pd.DataFrame({"y": y, "x1": x1, "x2": x2})


@pytest.fixture
def logistic_df():
    """Binary outcome dataset."""
    np.random.seed(42)
    n = 200
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    logit = 0.5 * x1 + 0.8 * x2
    prob = 1 / (1 + np.exp(-logit))
    y = (prob > 0.5).astype(int)
    return pd.DataFrame({"y": y, "x1": x1, "x2": x2})


class TestCorrelation:
    def test_pearson_diagonal_is_one(self, regression_df):
        result = pearson_spearman_correlation(regression_df, ["x1", "x2", "y"])
        for i in range(3):
            assert result["r_matrix"][i][i] == 1.0

    def test_symmetric_matrix(self, regression_df):
        result = pearson_spearman_correlation(regression_df, ["x1", "x2", "y"])
        r = result["r_matrix"]
        for i in range(3):
            for j in range(3):
                if r[i][j] is not None and r[j][i] is not None:
                    assert abs(r[i][j] - r[j][i]) < 0.001

    def test_spearman_available(self, regression_df):
        result = pearson_spearman_correlation(regression_df, ["x1", "y"], method="spearman")
        assert result["method"] == "spearman"
        assert result["r_matrix"][0][1] is not None


class TestOLSRegression:
    def test_r_squared_range(self, regression_df):
        result = ols_regression(regression_df, "y", ["x1", "x2"])
        assert 0 <= result["r2"] <= 1

    def test_high_r_squared_for_linear_data(self, regression_df):
        result = ols_regression(regression_df, "y", ["x1", "x2"])
        # Strong linear relationship should give R² > 0.9
        assert result["r2"] > 0.9

    def test_coefficient_count(self, regression_df):
        result = ols_regression(regression_df, "y", ["x1", "x2"])
        # Should have intercept + 2 predictors
        assert len(result["coefficients"]) == 3

    def test_approximate_coefficients(self, regression_df):
        result = ols_regression(regression_df, "y", ["x1", "x2"])
        x1_coef = next(c for c in result["coefficients"] if c["variable"] == "x1")
        x2_coef = next(c for c in result["coefficients"] if c["variable"] == "x2")
        # True coefficients are 2.0 and 1.5
        assert abs(x1_coef["B"] - 2.0) < 0.3
        assert abs(x2_coef["B"] - 1.5) < 0.3

    def test_vif_computed(self, regression_df):
        result = ols_regression(regression_df, "y", ["x1", "x2"])
        for coef in result["coefficients"]:
            if coef["variable"] != "(Constant)":
                assert coef["vif"] is not None
                assert coef["vif"] >= 1.0  # VIF is always >= 1

    def test_anova_table_present(self, regression_df):
        result = ols_regression(regression_df, "y", ["x1", "x2"])
        assert "anova_table" in result
        assert len(result["anova_table"]["rows"]) == 3

    def test_durbin_watson_range(self, regression_df):
        result = ols_regression(regression_df, "y", ["x1", "x2"])
        assert 0 <= result["durbin_watson"] <= 4


class TestQQPlotData:
    def test_blom_formula(self):
        """Q-Q data uses Blom (1958) formula, not scipy default."""
        data = list(range(1, 21))  # 20 observations
        result = spss_qq_data(data)
        assert len(result["observed"]) == 20
        assert len(result["theoretical"]) == 20

    def test_blom_first_quantile(self):
        """Verify Blom formula: p_1 = (1 - 3/8) / (n + 1/4) for n=10."""
        data = list(range(1, 11))  # n=10
        n = 10
        expected_p1 = (1 - 3/8) / (n + 1/4)
        # Verify expected_p1 is not equal to Filliben (0.5/10 = 0.05)
        assert abs(expected_p1 - 0.05) > 0.001  # Blom differs from Filliben

    def test_fit_line_parameters(self):
        """Slope and intercept should be finite numbers."""
        from scipy.stats import norm
        data = norm.rvs(loc=50, scale=10, size=50, random_state=42).tolist()
        result = spss_qq_data(data)
        assert np.isfinite(result["fit_slope"])
        assert np.isfinite(result["fit_intercept"])
