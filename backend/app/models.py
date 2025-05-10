"""
Database models for the DocTranscribe application.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserBase(SQLModel):
    """Base model for user data."""
    email: str = Field(index=True, unique=True)
    name: str
    is_active: bool = True
    role: UserRole = Field(default=UserRole.USER)


class User(UserBase, table=True):
    """Database model for user authentication and management."""
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    password: str  # Hashed password
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    documents: List["Document"] = Relationship(back_populates="user", sa_relationship_kwargs={"foreign_keys": "[Document.user_id]"})


class DocumentBase(SQLModel):
    """Base model for document metadata."""
    filename: str
    file_size: int
    mime_type: str = "application/pdf"
    total_pages: Optional[int] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class Document(DocumentBase, table=True):
    """Database model for storing document metadata."""
    __tablename__ = "document"
    __table_args__ = {"extend_existing": True}
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    
    # Relationships
    extraction_jobs: List["ExtractionJob"] = Relationship(back_populates="document", sa_relationship_kwargs={"foreign_keys": "[ExtractionJob.document_id]"})
    user: Optional["User"] = Relationship(back_populates="documents", sa_relationship_kwargs={"foreign_keys": "[Document.user_id]"})
    
    class Config:
        arbitrary_types_allowed = True


class ExtractionJobBase(SQLModel):
    """Base model for extraction job data."""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_name: str = "gpt-4.1"
    pages_processed: int = 0
    total_pages: int = 0
    confidence_score: Optional[float] = None
    error_message: Optional[str] = None


class ExtractionJob(ExtractionJobBase, table=True):
    """Database model for tracking extraction jobs."""
    __tablename__ = "extractionjob"
    __table_args__ = {"extend_existing": True}
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="document.id")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    
    # Relationships
    document: "Document" = Relationship(back_populates="extraction_jobs", sa_relationship_kwargs={"foreign_keys": "[ExtractionJob.document_id]"})
    results: List["ExtractionResult"] = Relationship(back_populates="job", sa_relationship_kwargs={"foreign_keys": "[ExtractionResult.job_id]"})


class ExtractionResultBase(SQLModel):
    """Base model for extraction results."""
    page_number: int
    processing_time: float  # in seconds
    confidence_score: Optional[float] = None


class ExtractionResult(ExtractionResultBase, table=True):
    """Database model for storing extraction results."""
    __tablename__ = "extractionresult"
    __table_args__ = {"extend_existing": True}
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="extractionjob.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Using SQLAlchemy JSON type for the content field
    content: dict = Field(sa_column=Column(JSON))
    
    # Relationships
    job: "ExtractionJob" = Relationship(back_populates="results", sa_relationship_kwargs={"foreign_keys": "[ExtractionResult.job_id]"})


class XLSXExportBase(SQLModel):
    """Base model for XLSX export metadata."""
    filename: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    file_size: Optional[int] = None
    s3_key: Optional[str] = None  # S3 storage key if using S3
    local_path: Optional[str] = None  # Local file path if using local storage


class XLSXExport(XLSXExportBase, table=True):
    """Database model for tracking XLSX exports."""
    __tablename__ = "xlsxexport"
    __table_args__ = {"extend_existing": True}
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="extractionjob.id")
    
    # Relationships
    job: "ExtractionJob" = Relationship(sa_relationship_kwargs={"foreign_keys": "[XLSXExport.job_id]"}) 