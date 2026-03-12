"""
Data Transform Routes
Recode, Compute, Filter, Sort operations — all update SESSION_STORE in-place
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException

from app.domain.services.spss_io import get_session, update_session
from app.domain.services.transforms import (
    recode_variable, compute_variable, select_cases, sort_cases, rank_cases
)
from app.api.schemas.transform import (
    RecodeRequest, ComputeRequest, FilterRequest, SortRequest, RankRequest
)
from app.core.exceptions import StatisticalError

logger = logging.getLogger(__name__)
router = APIRouter()


def _meta_dict(meta):
    return {
        "file_name": meta.file_name,
        "n_cases": meta.n_cases,
        "n_vars": meta.n_vars,
        "encoding": meta.encoding,
    }


@router.post("/{session_id}/recode")
async def recode_route(session_id: str, payload: RecodeRequest):
    df, meta = get_session(session_id)
    try:
        new_df = await asyncio.to_thread(
            recode_variable,
            df,
            payload.source_var,
            payload.target_var,
            [r.model_dump() for r in payload.rules],
            payload.else_value,
        )
        new_meta = meta.model_copy(update={"n_cases": len(new_df), "n_vars": len(new_df.columns)})
        update_session(session_id, new_df, new_meta)
        return {
            "session_id": session_id,
            "meta": _meta_dict(new_meta),
            "n_cases": len(new_df),
            "message": f"Recoded '{payload.source_var}' → '{payload.target_var}'"
        }
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Recode error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Recode failed: {str(e)}")


@router.post("/{session_id}/compute")
async def compute_route(session_id: str, payload: ComputeRequest):
    df, meta = get_session(session_id)
    try:
        new_df = await asyncio.to_thread(
            compute_variable,
            df,
            payload.target_var,
            payload.expression,
            payload.label,
        )
        new_meta = meta.model_copy(update={"n_cases": len(new_df), "n_vars": len(new_df.columns)})
        update_session(session_id, new_df, new_meta)
        return {
            "session_id": session_id,
            "meta": _meta_dict(new_meta),
            "n_cases": len(new_df),
            "message": f"Computed '{payload.target_var}' = {payload.expression}"
        }
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Compute error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Compute failed: {str(e)}")


@router.post("/{session_id}/filter")
async def filter_route(session_id: str, payload: FilterRequest):
    df, meta = get_session(session_id)
    original_n = len(df)
    try:
        new_df = await asyncio.to_thread(
            select_cases,
            df,
            payload.condition,
            payload.filter_type,
        )
        new_meta = meta.model_copy(update={"n_cases": len(new_df)})
        update_session(session_id, new_df, new_meta)
        removed = original_n - len(new_df)
        return {
            "session_id": session_id,
            "meta": _meta_dict(new_meta),
            "n_cases": len(new_df),
            "n_filtered": removed,
            "message": f"Filter applied: {len(new_df)} cases retained, {removed} {'excluded' if payload.filter_type == 'exclude' else 'removed'}"
        }
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Filter error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Filter failed: {str(e)}")


@router.post("/{session_id}/sort")
async def sort_route(session_id: str, payload: SortRequest):
    df, meta = get_session(session_id)
    try:
        new_df = await asyncio.to_thread(
            sort_cases,
            df,
            payload.sort_keys,
        )
        update_session(session_id, new_df, meta)
        sort_desc = ", ".join(
            f"{k['variable']} {'↑' if k.get('order','asc').lower() != 'desc' else '↓'}"
            for k in payload.sort_keys
        )
        return {
            "session_id": session_id,
            "meta": _meta_dict(meta),
            "n_cases": len(new_df),
            "message": f"Sorted by: {sort_desc}"
        }
    except HTTPException:
        raise
    except (ValueError, StatisticalError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Sort error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sort failed: {str(e)}")
