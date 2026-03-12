"""
Integration tests — Full API endpoint tests using httpx AsyncClient.
"""
import io
import pytest
import pandas as pd
import numpy as np
import httpx
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def csv_file():
    """Create an in-memory CSV file for upload testing."""
    np.random.seed(42)
    df = pd.DataFrame({
        "id": range(1, 51),
        "age": np.random.randint(20, 35, 50),
        "score": np.random.normal(75, 10, 50).round(2),
        "gender": np.random.choice([1, 2], 50),
        "group": np.random.choice([1, 2, 3], 50),
    })
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.read().encode("utf-8")


class TestHealth:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "sessions" in data


class TestFileUpload:
    def test_upload_csv(self, client, csv_file):
        response = client.post(
            "/files/upload",
            files={"file": ("test.csv", csv_file, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["meta"]["n_cases"] == 50
        assert data["meta"]["n_vars"] == 5
        return data["session_id"]

    def test_get_data(self, client, csv_file):
        upload_resp = client.post(
            "/files/upload",
            files={"file": ("test.csv", csv_file, "text/csv")},
        )
        session_id = upload_resp.json()["session_id"]

        data_resp = client.get(f"/files/{session_id}/data?page=1&page_size=10")
        assert data_resp.status_code == 200
        data = data_resp.json()
        assert len(data["data"]) == 10
        assert data["total"] == 50

    def test_invalid_format_rejected(self, client):
        response = client.post(
            "/files/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 400

    def test_delete_session(self, client, csv_file):
        upload_resp = client.post(
            "/files/upload",
            files={"file": ("test.csv", csv_file, "text/csv")},
        )
        session_id = upload_resp.json()["session_id"]

        del_resp = client.delete(f"/files/{session_id}")
        assert del_resp.status_code == 200

        get_resp = client.get(f"/files/{session_id}/meta")
        assert get_resp.status_code == 404


class TestDescriptives:
    @pytest.fixture(autouse=True)
    def upload_session(self, client, csv_file):
        resp = client.post("/files/upload", files={"file": ("t.csv", csv_file, "text/csv")})
        self.session_id = resp.json()["session_id"]

    def test_frequencies(self, client):
        resp = client.post("/descriptives/frequencies", json={
            "session_id": self.session_id,
            "variable": "gender",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
        assert data["n_total"] == 50

    def test_descriptives(self, client):
        resp = client.post("/descriptives/descriptives", json={
            "session_id": self.session_id,
            "variables": ["score", "age"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rows"]) == 2


class TestHypothesisTests:
    @pytest.fixture(autouse=True)
    def upload_session(self, client, csv_file):
        resp = client.post("/files/upload", files={"file": ("t.csv", csv_file, "text/csv")})
        self.session_id = resp.json()["session_id"]

    def test_independent_ttest(self, client):
        resp = client.post("/tests/ttest/independent", json={
            "session_id": self.session_id,
            "group_var": "gender",
            "test_var": "score",
            "equal_var": True,
            "alternative": "two-sided",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "statistic" in data
        assert "pvalue" in data
        assert 0 <= data["pvalue"] <= 1

    def test_one_way_anova(self, client):
        resp = client.post("/tests/anova/one-way", json={
            "session_id": self.session_id,
            "group_var": "group",
            "dep_var": "score",
            "posthoc": "tukey",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "f_statistic" in data
        assert "p_value" in data


class TestRegression:
    @pytest.fixture(autouse=True)
    def upload_session(self, client, csv_file):
        resp = client.post("/files/upload", files={"file": ("t.csv", csv_file, "text/csv")})
        self.session_id = resp.json()["session_id"]

    def test_linear_regression(self, client):
        resp = client.post("/regression/linear", json={
            "session_id": self.session_id,
            "dependent": "score",
            "independents": ["age"],
            "method": "enter",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "r2" in data
        assert 0 <= data["r2"] <= 1
        assert "coefficients" in data
