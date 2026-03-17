"""
File I/O Routes — Upload, read, export SPSS/CSV/Excel files
DISK SAFETY: All temp files use statworks_ prefix and are cleaned in finally blocks.
"""
import os
import logging

from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from app.domain.services.spss_io import (
    SESSION_STORE, read_file, create_session, get_session,
    update_session, delete_session, df_to_json_safe, write_sav
)
from app.domain.models.dataset import DatasetMeta
from app.api.schemas.files import (
    UploadResponse, DataPageResponse, UpdateMetaRequest
)
from app.core.config import settings
from app.core.cleanup import make_temp_path

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".sav"}


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a data file (.csv, .xlsx, .sav). Returns session_id + metadata."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    from pathlib import Path
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.MAX_UPLOAD_MB}MB"
        )

    tmp_path = None
    try:
        tmp_path = make_temp_path(suffix=ext)
        with open(tmp_path, "wb") as f:
            f.write(content)

        df, meta = read_file(tmp_path, ext.lstrip("."))
        session_id = create_session(df, meta)

        from datetime import datetime
        return UploadResponse(
            session_id=session_id,
            meta=meta,
            created_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/{session_id}/data", response_model=DataPageResponse)
async def get_data(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000)
):
    """Return paginated rows for the data grid."""
    df, meta = get_session(session_id)
    total = len(df)
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df.iloc[start:end]

    return DataPageResponse(
        data=df_to_json_safe(page_df),
        total=total,
        page=page,
        page_size=page_size,
        n_vars=len(df.columns),
    )


@router.get("/{session_id}/meta", response_model=DatasetMeta)
async def get_meta(session_id: str):
    """Return DatasetMeta for a session."""
    _, meta = get_session(session_id)
    return meta


@router.put("/{session_id}/meta", response_model=DatasetMeta)
async def update_meta(session_id: str, body: UpdateMetaRequest):
    """Update variable metadata (labels, measure, missing, etc.)."""
    df, meta = get_session(session_id)

    if body.variables is not None:
        meta = meta.model_copy(update={"variables": body.variables})
    if body.file_name is not None:
        meta = meta.model_copy(update={"file_name": body.file_name})

    update_session(session_id, df, meta)
    return meta


def _remove_file(path: str):
    """Background task to remove temp file after response is sent."""
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


@router.post("/{session_id}/export/sav")
async def export_sav(session_id: str):
    """Export session data as SPSS .sav file."""
    df, meta = get_session(session_id)
    tmp_path = make_temp_path(suffix=".sav")

    try:
        write_sav(df, meta, tmp_path)
        filename = meta.file_name.replace(".csv", ".sav").replace(".xlsx", ".sav")
        if not filename.endswith(".sav"):
            filename = filename + ".sav"
        return FileResponse(
            path=tmp_path,
            media_type="application/octet-stream",
            filename=filename,
            background=BackgroundTask(_remove_file, tmp_path),
        )
    except Exception as e:
        _remove_file(tmp_path)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.delete("/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Delete a session and free memory."""
    delete_session(session_id)
    return {"message": f"Session {session_id} deleted"}


@router.get("/health")
async def files_health():
    """Return session count (used by keep-warm cron)."""
    return {"status": "ok", "sessions": len(SESSION_STORE)}
