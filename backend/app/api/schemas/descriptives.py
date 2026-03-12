from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class FrequencyRequest(BaseModel):
    session_id: str
    variable: str
    include_charts: bool = False
    cumulative: bool = True


class FrequencyRow(BaseModel):
    value: Any
    label: str = ""
    count: int
    percent: float
    valid_percent: float
    cumulative_percent: float


class FrequencyResponse(BaseModel):
    variable: str
    label: str = ""
    rows: List[Any]
    row_details: List[FrequencyRow] = []
    n_valid: int
    n_missing: int
    n_total: int
    mode: Optional[Any] = None
    headers: List[str] = ["Value", "Label", "Count", "Percent", "Valid %", "Cumul. %"]


class DescriptivesRequest(BaseModel):
    session_id: str
    variables: List[str]


class DescriptivesRow(BaseModel):
    variable: str
    label: str = ""
    n: int
    mean: Optional[float]
    std_dev: Optional[float]
    variance: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]
    range: Optional[float]
    skewness: Optional[float]
    std_error_skew: Optional[float]
    kurtosis: Optional[float]
    std_error_kurt: Optional[float]
    se_mean: Optional[float]
    median: Optional[float]
    sum: Optional[float]


class DescriptivesResponse(BaseModel):
    rows: List[DescriptivesRow]
    headers: List[str] = ["Variable", "N", "Mean", "Std Dev", "Variance", "Min", "Max", "Range", "Skewness", "Kurtosis"]


class CrosstabRequest(BaseModel):
    session_id: str
    row_var: str
    col_var: str
    include_chi2: bool = True
    include_cramers_v: bool = True
    row_percentages: bool = True
    col_percentages: bool = True


class CrosstabResponse(BaseModel):
    row_var: str
    col_var: str
    table: Dict[str, Any]  # crosstab as nested dict
    chi2: Optional[float] = None
    df: Optional[int] = None
    p_value: Optional[float] = None
    cramers_v: Optional[float] = None
    phi: Optional[float] = None
    fisher_exact_p: Optional[float] = None
    n: int
    headers: List[str] = []
    rows: List[Any] = []


class ExploreRequest(BaseModel):
    session_id: str
    variable: str
    factor_var: Optional[str] = None


class ExploreResponse(BaseModel):
    variable: str
    shapiro_w: Optional[float] = None
    shapiro_p: Optional[float] = None
    boxplot_stats: Optional[Dict[str, Any]] = None
    percentiles: Optional[Dict[str, float]] = None
    n_valid: int
    n_missing: int
