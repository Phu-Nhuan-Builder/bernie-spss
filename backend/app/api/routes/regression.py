"""
Regression & Correlation Routes — with full error handling
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException

from app.domain.services.spss_io import get_session
from app.domain.services.regression import (
    pearson_spearman_correlation, ols_regression, binary_logistic
)
from app.api.schemas.regression import CorrelationRequest, RegressionRequest, LogisticRequest
from app.core.exceptions import StatisticalError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/correlation")
async def correlation_route(payload: CorrelationRequest):
    try:
        df, meta = get_session(payload.session_id)
        if len(payload.variables) < 2:
            raise HTTPException(status_code=422, detail="At least 2 variables required for correlation")
        missing = [v for v in payload.variables if v not in df.columns]
        if missing:
            raise HTTPException(status_code=422, detail=f"Variables not found: {missing}")
        result = await asyncio.to_thread(
            pearson_spearman_correlation, df, payload.variables, payload.method
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Correlation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Correlation computation failed: {str(e)}")


@router.post("/linear")
async def linear_regression_route(payload: RegressionRequest):
    try:
        df, meta = get_session(payload.session_id)
        if payload.dependent not in df.columns:
            raise HTTPException(status_code=422, detail=f"Dependent variable '{payload.dependent}' not found")
        missing = [v for v in payload.independents if v not in df.columns]
        if missing:
            raise HTTPException(status_code=422, detail=f"Independent variables not found: {missing}")
        if len(payload.independents) == 0:
            raise HTTPException(status_code=422, detail="At least one independent variable required")
        result = await asyncio.to_thread(
            ols_regression, df, payload.dependent, payload.independents,
            payload.method, payload.include_diagnostics
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Linear regression error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Linear regression failed: {str(e)}")


@router.post("/logistic/binary")
async def logistic_binary_route(payload: LogisticRequest):
    try:
        df, meta = get_session(payload.session_id)
        if payload.dependent not in df.columns:
            raise HTTPException(status_code=422, detail=f"Dependent variable '{payload.dependent}' not found")
        missing = [v for v in payload.independents if v not in df.columns]
        if missing:
            raise HTTPException(status_code=422, detail=f"Independent variables not found: {missing}")
        # Check binary dependent
        unique_vals = df[payload.dependent].dropna().unique()
        if len(unique_vals) != 2:
            raise HTTPException(
                status_code=422,
                detail=f"Dependent variable must be binary (2 unique values), found {len(unique_vals)}: {unique_vals[:5].tolist()}"
            )
        result = await asyncio.to_thread(
            binary_logistic, df, payload.dependent, payload.independents
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Logistic regression error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Logistic regression failed: {str(e)}")
