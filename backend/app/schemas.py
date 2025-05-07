from pydantic import BaseModel, Field
from typing import List, Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


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
    
# Response model for the job that matches frontend expectations
class JobResult(BaseModel):
    sheet_name: str
    anomalies: int


class PDFMetadataResponse(BaseModel):
    filename: str
    filesize_bytes: int
    page_count: int
    summary: str


class XLSXSignedURLResponse(BaseModel):
    url: str


# Batch processing schemas
class BatchJobRequest(BaseModel):
    """Request for creating a batch job to process multiple PDFs"""
    name: Optional[str] = Field(None, description="Optional batch name")
    file_count: Optional[int] = Field(1, description="Number of files to process")


class BatchJobResult(BaseModel):
    """Response for a batch job creation"""
    batch_id: str = Field(..., description="Unique identifier for the batch job")
    name: str = Field(..., description="Name of the batch job")
    status: str = Field(..., description="Current status of the batch (queued, processing, completed, failed)")
    message: Optional[str] = Field(None, description="Optional status message")


# class PDFUpload(SQLModel, table=True):
#     __tablename__ = "pdfupload"
#     __table_args__ = {"extend_existing": True}
#     id: int = Field(default=None, primary_key=True)
#     filename: str
#     filesize_bytes: int
#     page_count: int
#     summary: str
#     uploaded_at: datetime = Field(default_factory=datetime.utcnow) 