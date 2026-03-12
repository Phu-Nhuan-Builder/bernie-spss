"""
Export Routes — PDF and Excel file download endpoints
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.domain.services.export import export_pdf, export_excel
from app.api.schemas.export import ExportRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/pdf")
async def export_pdf_route(payload: ExportRequest):
    """Generate and stream a PDF of the output blocks."""
    import asyncio

    if not payload.output_blocks:
        raise HTTPException(status_code=400, detail="No output blocks provided")

    try:
        blocks = [block.model_dump() for block in payload.output_blocks]
        title = payload.title or "Statistical Output"
        pdf_bytes = await asyncio.to_thread(export_pdf, blocks, title)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="bernie-spss-output.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"PDF export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/excel")
async def export_excel_route(payload: ExportRequest):
    """Generate and stream an Excel workbook of the output blocks."""
    import asyncio

    if not payload.output_blocks:
        raise HTTPException(status_code=400, detail="No output blocks provided")

    try:
        blocks = [block.model_dump() for block in payload.output_blocks]
        title = payload.title or "Statistical Output"
        excel_bytes = await asyncio.to_thread(export_excel, blocks, title)

        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="bernie-spss-output.xlsx"',
                "Content-Length": str(len(excel_bytes)),
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Excel export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {str(e)}")
