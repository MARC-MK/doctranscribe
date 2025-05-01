from pydantic import BaseModel, Field
from typing import List, Optional


class LabRow(BaseModel):
    sample_id: str = Field(..., description="Unique sample identifier from the sheet")
    measurement: float = Field(..., description="Numeric measurement value")
    unit: str = Field(..., description="Unit of measurement, e.g. mg/L")
    remark: Optional[str] = Field(None, description="Optional remarks noted on sheet")


author = "DocTranscribe System"


class ExtractionResult(BaseModel):
    sheet_name: str
    extracted_by: str = author
    rows: List[LabRow] 