"""
AI Analysis Routes — Natural language → Statistical insights
POST /ai/analyze     — NL query analysis
POST /ai/analyze-auto — One-click full analysis
POST /ai/generate-report — Structured report
GET  /ai/schema/{session_id} — Dataset schema
"""
import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas.ai import (
    AnalyzeRequest, AnalyzeResponse,
    AnalyzeAutoRequest, AnalyzeAutoResponse,
    GenerateReportRequest, ReportResponse,
    SchemaResponse,
)
from app.services.orchestrator import analyze, analyze_auto, generate_full_report
from app.services.schema_inference import infer_schema
from app.domain.services.spss_io import get_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def ai_analyze(body: AnalyzeRequest):
    """
    Natural Language → Statistical Analysis → Insights.
    
    Send a query like:
    - "Compare two groups"
    - "What affects sales the most?"
    - "Find relationship between variables"
    
    The system will:
    1. Parse your intent using AI
    2. Select the correct statistical method
    3. Execute the analysis
    4. Return results with human-readable insights
    """
    try:
        result = await analyze(body.session_id, body.query)
        return AnalyzeResponse(**result)
    except Exception as e:
        logger.error(f"AI analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-auto", response_model=AnalyzeAutoResponse)
async def ai_analyze_auto(body: AnalyzeAutoRequest):
    """
    One-click "Analyze for me" — Full autonomous analysis pipeline.
    
    Upload a dataset, then call this endpoint. The system will:
    1. Infer the schema (numeric vs categorical variables)
    2. Auto-select appropriate statistical methods
    3. Run descriptives, correlations, comparisons, regression
    4. Generate insights for each analysis
    """
    try:
        result = await analyze_auto(body.session_id)
        return AnalyzeAutoResponse(**result)
    except Exception as e:
        logger.error(f"AI auto-analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-report", response_model=ReportResponse)
async def ai_generate_report(body: GenerateReportRequest):
    """
    Generate a structured statistical report.
    
    Returns an academic-style report with:
    - Introduction
    - Methodology
    - Results
    - Discussion
    - Conclusion
    
    If no analyses are provided, runs auto-analysis first.
    """
    try:
        result = await generate_full_report(body.session_id, body.analyses)
        return ReportResponse(**result)
    except Exception as e:
        logger.error(f"Report generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/{session_id}", response_model=SchemaResponse)
async def ai_schema(session_id: str):
    """
    Return the inferred schema for a dataset session.
    Shows which variables are numeric, categorical, date, etc.
    """
    try:
        df, _ = get_session(session_id)
        schema = infer_schema(df)
        return SchemaResponse(**schema)
    except Exception as e:
        logger.error(f"Schema inference error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
