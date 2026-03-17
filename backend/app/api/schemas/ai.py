"""Pydantic schemas for AI analysis endpoints."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from file upload")
    query: str = Field(..., description="Natural language query, e.g. 'Compare groups' or 'What affects sales?'")


class AnalyzeAutoRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from file upload")


class GenerateReportRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from file upload")
    analyses: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional: pre-computed analysis results. If empty, runs auto-analysis first."
    )


class InsightResponse(BaseModel):
    headline: str = ""
    interpretation: str = ""
    significance: str = ""
    recommendations: List[str] = Field(default_factory=list)


class ChartSpec(BaseModel):
    chart_type: str = Field(..., description="bar | scatter | heatmap | boxplot | line")
    title: str = ""
    x: Optional[List[Any]] = None
    y: Optional[List[Any]] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    x_labels: Optional[List[str]] = None
    y_labels: Optional[List[str]] = None
    z: Optional[List[List[Any]]] = None
    error_y: Optional[List[Any]] = None
    data: Optional[Dict[str, Any]] = None
    color_scale: Optional[str] = None
    reference_line: Optional[float] = None


class TableSpec(BaseModel):
    title: str = ""
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)


class AnalysisMeta(BaseModel):
    analysis_type: str = ""
    confidence: float = 0.0


class AnalysisItem(BaseModel):
    method: str
    description: str
    results: Optional[Dict[str, Any]] = None
    insight: Optional[InsightResponse] = None
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    status: str
    intent: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    insight: Optional[InsightResponse] = None
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    meta: Optional[AnalysisMeta] = None
    message: Optional[str] = None
    dataset_schema: Optional[Dict[str, Any]] = None


class AnalyzeAutoResponse(BaseModel):
    status: str
    dataset_schema: Optional[Dict[str, Any]] = None
    n_analyses: int = 0
    analyses: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None


class ReportSection(BaseModel):
    heading: str
    content: str


class ReportResponse(BaseModel):
    status: str
    report: Optional[Dict[str, Any]] = None
    n_analyses: int = 0
    message: Optional[str] = None


class SchemaResponse(BaseModel):
    n_rows: int
    n_cols: int
    variables: List[Dict[str, Any]]
    numeric_vars: List[str]
    categorical_vars: List[str]
    summary_text: str
