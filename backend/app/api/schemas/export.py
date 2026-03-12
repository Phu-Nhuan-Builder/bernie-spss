from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class OutputBlockData(BaseModel):
    id: str
    type: str  # "table" or "chart"
    title: str
    subtitle: Optional[str] = None
    procedure: str
    content: Any


class ExportRequest(BaseModel):
    output_blocks: List[OutputBlockData]
    title: Optional[str] = "Statistical Output"
    session_id: Optional[str] = None
    format: Optional[str] = None  # "pdf" or "excel" — inferred from endpoint
    include_footer: bool = True
