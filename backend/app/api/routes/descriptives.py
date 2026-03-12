"""
Descriptives Routes — with full error handling
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException

from app.domain.services.spss_io import get_session
from app.domain.services.descriptives import (
    compute_frequencies, compute_descriptives, compute_crosstabs, compute_explore
)
from app.api.schemas.descriptives import (
    FrequencyRequest, DescriptivesRequest, CrosstabRequest, ExploreRequest
)
from app.core.exceptions import StatisticalError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/frequencies")
async def frequencies(payload: FrequencyRequest):
    try:
        df, meta = get_session(payload.session_id)
        value_labels = {}
        for v in meta.variables:
            if v.name == payload.variable:
                value_labels = v.value_labels or {}
                break
        if payload.variable not in df.columns:
            raise HTTPException(status_code=422, detail=f"Variable '{payload.variable}' not found in dataset")
        result = await asyncio.to_thread(
            compute_frequencies, df, payload.variable, value_labels
        )
        return result
    except HTTPException:
        raise
    except StatisticalError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": e.message})
    except Exception as e:
        logger.error(f"Frequencies error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Frequencies computation failed: {str(e)}")


@router.post("/descriptives")
async def descriptives(payload: DescriptivesRequest):
    try:
        df, meta = get_session(payload.session_id)
        missing = [v for v in payload.variables if v not in df.columns]
        if missing:
            raise HTTPException(status_code=422, detail=f"Variables not found: {missing}")
        result = await asyncio.to_thread(
            compute_descriptives, df, payload.variables
        )
        return result
    except HTTPException:
        raise
    except StatisticalError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": e.message})
    except Exception as e:
        logger.error(f"Descriptives error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Descriptives computation failed: {str(e)}")


@router.post("/crosstabs")
async def crosstabs(payload: CrosstabRequest):
    try:
        df, meta = get_session(payload.session_id)
        row_vl = {}
        col_vl = {}
        for v in meta.variables:
            if v.name == payload.row_var:
                row_vl = v.value_labels or {}
            if v.name == payload.col_var:
                col_vl = v.value_labels or {}
        for var in [payload.row_var, payload.col_var]:
            if var not in df.columns:
                raise HTTPException(status_code=422, detail=f"Variable '{var}' not found in dataset")
        result = await asyncio.to_thread(
            compute_crosstabs, df, payload.row_var, payload.col_var, row_vl, col_vl
        )
        return result
    except HTTPException:
        raise
    except StatisticalError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": e.message})
    except Exception as e:
        logger.error(f"Crosstabs error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Crosstabs computation failed: {str(e)}")


@router.post("/explore")
async def explore(payload: ExploreRequest):
    try:
        df, meta = get_session(payload.session_id)
        if payload.variable not in df.columns:
            raise HTTPException(status_code=422, detail=f"Variable '{payload.variable}' not found in dataset")
        result = await asyncio.to_thread(
            compute_explore, df, payload.variable
        )
        return result
    except HTTPException:
        raise
    except StatisticalError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": e.message})
    except Exception as e:
        logger.error(f"Explore error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Explore computation failed: {str(e)}")
