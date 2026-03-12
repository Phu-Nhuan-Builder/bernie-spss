"""
Hypothesis Tests Routes — with full error handling
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException

from app.domain.services.spss_io import get_session
from app.domain.services.tests import (
    independent_ttest, paired_ttest, one_sample_ttest, one_way_anova, compute_means
)
from app.api.schemas.tests import TTestRequest, ANOVARequest, MeansRequest
from app.core.exceptions import StatisticalError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ttest/independent")
async def independent_ttest_route(payload: TTestRequest):
    try:
        df, meta = get_session(payload.session_id)
        if not payload.group_var or not payload.test_var:
            raise HTTPException(status_code=422, detail="group_var and test_var are required")
        for var in [payload.group_var, payload.test_var]:
            if var not in df.columns:
                raise HTTPException(status_code=422, detail=f"Variable '{var}' not found in dataset")
        result = await asyncio.to_thread(
            independent_ttest,
            df,
            payload.group_var,
            payload.test_var,
            payload.equal_var,
            payload.alternative,
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Independent t-test error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"T-test computation failed: {str(e)}")


@router.post("/ttest/paired")
async def paired_ttest_route(payload: TTestRequest):
    try:
        df, meta = get_session(payload.session_id)
        if not payload.var1 or not payload.var2:
            raise HTTPException(status_code=422, detail="var1 and var2 are required for paired t-test")
        for var in [payload.var1, payload.var2]:
            if var not in df.columns:
                raise HTTPException(status_code=422, detail=f"Variable '{var}' not found in dataset")
        result = await asyncio.to_thread(
            paired_ttest, df, payload.var1, payload.var2
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Paired t-test error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Paired t-test computation failed: {str(e)}")


@router.post("/ttest/one-sample")
async def one_sample_ttest_route(payload: TTestRequest):
    try:
        df, meta = get_session(payload.session_id)
        if not payload.variable:
            raise HTTPException(status_code=422, detail="variable is required for one-sample t-test")
        if payload.variable not in df.columns:
            raise HTTPException(status_code=422, detail=f"Variable '{payload.variable}' not found in dataset")
        result = await asyncio.to_thread(
            one_sample_ttest, df, payload.variable, payload.test_value or 0.0
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"One-sample t-test error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"One-sample t-test computation failed: {str(e)}")


@router.post("/anova/one-way")
async def one_way_anova_route(payload: ANOVARequest):
    try:
        df, meta = get_session(payload.session_id)
        for var in [payload.group_var, payload.dep_var]:
            if var not in df.columns:
                raise HTTPException(status_code=422, detail=f"Variable '{var}' not found in dataset")
        result = await asyncio.to_thread(
            one_way_anova, df, payload.group_var, payload.dep_var, payload.posthoc
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"One-way ANOVA error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ANOVA computation failed: {str(e)}")


@router.post("/means")
async def means_route(payload: MeansRequest):
    try:
        df, meta = get_session(payload.session_id)
        for var in [payload.dep_var, payload.factor_var]:
            if var not in df.columns:
                raise HTTPException(status_code=422, detail=f"Variable '{var}' not found in dataset")
        result = await asyncio.to_thread(
            compute_means, df, payload.dep_var, payload.factor_var
        )
        return result
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Means error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Means computation failed: {str(e)}")
