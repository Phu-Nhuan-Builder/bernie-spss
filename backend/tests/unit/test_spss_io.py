"""
Unit tests for SPSS I/O service — encoding, session management, box plots, Q-Q.
"""
import os
import pytest
import pandas as pd
import numpy as np

from app.domain.services.spss_io import (
    read_csv, create_session, get_session, delete_session, df_to_json_safe,
    resolve_encoding, SESSION_STORE
)
from app.core.exceptions import SessionNotFoundError


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class TestCSVReading:
    def test_read_sample_csv(self):
        csv_path = os.path.join(FIXTURES_DIR, "sample.csv")
        df, meta = read_csv(csv_path)
        assert len(df) == 50
        assert "id" in df.columns
        assert meta.n_cases == 50
        assert meta.n_vars == 5

    def test_meta_variables(self):
        csv_path = os.path.join(FIXTURES_DIR, "sample.csv")
        _, meta = read_csv(csv_path)
        var_names = [v.name for v in meta.variables]
        assert "age" in var_names
        assert "score" in var_names
        assert "gender" in var_names

    def test_encoding_utf8(self):
        result = resolve_encoding("/dev/null", "utf-8")
        assert result == "utf-8"


class TestSessionManagement:
    def test_create_and_get_session(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        from app.domain.models.dataset import DatasetMeta, VariableMeta, VariableType, VariableMeasure, VariableRole
        meta = DatasetMeta(
            file_name="test.csv",
            n_cases=3,
            n_vars=2,
            variables=[
                VariableMeta(name="a", var_type=VariableType.numeric, measure=VariableMeasure.scale, role=VariableRole.input),
                VariableMeta(name="b", var_type=VariableType.numeric, measure=VariableMeasure.scale, role=VariableRole.input),
            ],
            encoding="utf-8"
        )
        session_id = create_session(df, meta)
        assert session_id in SESSION_STORE

        retrieved_df, retrieved_meta = get_session(session_id)
        assert len(retrieved_df) == 3
        assert retrieved_meta.file_name == "test.csv"

        delete_session(session_id)
        assert session_id not in SESSION_STORE

    def test_get_nonexistent_session(self):
        with pytest.raises(SessionNotFoundError):
            get_session("nonexistent-session-id-12345")


class TestJsonSerialization:
    def test_nan_becomes_none(self):
        df = pd.DataFrame({"a": [1.0, float("nan"), 3.0]})
        records = df_to_json_safe(df)
        assert records[1]["a"] is None

    def test_numpy_int_serialized(self):
        import numpy as np
        df = pd.DataFrame({"a": np.array([1, 2, 3], dtype=np.int64)})
        records = df_to_json_safe(df)
        assert records[0]["a"] == 1
        assert isinstance(records[0]["a"], int)

    def test_numpy_float_serialized(self):
        import numpy as np
        df = pd.DataFrame({"a": np.array([1.5, 2.5], dtype=np.float64)})
        records = df_to_json_safe(df)
        assert abs(records[0]["a"] - 1.5) < 0.001


class TestBoxPlotStats:
    def test_whiskers_are_data_points(self):
        """EXACT: whiskers must be actual data points, not fence boundaries."""
        from app.domain.services.descriptives import spss_boxplot_stats
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50]
        result = spss_boxplot_stats(data)
        # 50 is an outlier; whisker_high must be 10 (last non-outlier)
        assert result["whisker_high"] == 10
        assert result["whisker_low"] == 1  # min non-outlier

    def test_iqr_whisker_calculation(self):
        from app.domain.services.descriptives import spss_boxplot_stats
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        result = spss_boxplot_stats(data)
        assert "q1" in result
        assert "q3" in result
        assert "median" in result
        assert result["q1"] <= result["median"] <= result["q3"]


class TestCronbachAlpha:
    def test_cronbach_alpha_matches_pingouin(self):
        """Cronbach's alpha must match pingouin (which matches SPSS with ddof=1)."""
        import pingouin as pg
        from app.domain.services.factor_analysis import run_reliability

        np.random.seed(42)
        df = pd.DataFrame(np.random.normal(0, 1, (100, 4)), columns=["i1", "i2", "i3", "i4"])

        result = run_reliability(df, ["i1", "i2", "i3", "i4"])
        ref_alpha, _ = pg.cronbach_alpha(data=df[["i1", "i2", "i3", "i4"]])

        assert abs(result["cronbach_alpha"] - float(ref_alpha)) < 0.01
