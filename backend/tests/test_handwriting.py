"""
Tests for the handwriting recognition API.
"""
import os
import uuid
from typing import Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import Document, ExtractionJob, ProcessingStatus, User, UserRole

# Use in-memory SQLite for testing
@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="session")
def session_fixture(engine: Generator) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client."""
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    # Mock authentication
    with patch("app.auth.get_current_user") as mock_get_current_user:
        # Create mock user
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            name="Test User",
            password="hashed_password",
            role=UserRole.USER
        )
        mock_get_current_user.return_value = user
        
        with TestClient(app) as client:
            yield client
    
    app.dependency_overrides.clear()

def test_handwriting_test_endpoint(client: TestClient):
    """Test the handwriting test endpoint."""
    response = client.post("/handwriting/test")
    
    assert response.status_code == 200
    assert response.json()["status"] == "operational"
    assert response.json()["model"] == "gpt-4.1"

def test_upload_document_endpoint(client: TestClient, session: Session):
    """Test the upload document endpoint."""
    # Mock the save_uploaded_file method to avoid actual file operations
    with patch("app.services.pdf_service.PDFProcessingService.save_uploaded_file") as mock_save:
        # Create a mock document
        document_id = uuid.uuid4()
        mock_document = Document(
            id=document_id,
            filename="test.pdf",
            file_size=1024,
            status=ProcessingStatus.PENDING,
            total_pages=5
        )
        mock_save.return_value = mock_document
        
        # Call the endpoint with a mock file
        with open("tests/fixtures/handwriting_samples/mental_health_survey_v4.pdf", "rb") as f:
            response = client.post(
                "/handwriting/upload",
                files={"file": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        assert response.json()["filename"] == "test.pdf"
        assert response.json()["status"] == "pending"
        assert response.json()["total_pages"] == 5

def test_get_document_endpoint(client: TestClient, session: Session):
    """Test the get document endpoint."""
    # Create a test document
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        filename="test.pdf",
        file_size=1024,
        status=ProcessingStatus.PENDING,
        total_pages=5
    )
    session.add(document)
    session.commit()
    
    # Call the endpoint
    response = client.get(f"/handwriting/documents/{document_id}")
    
    assert response.status_code == 200
    assert response.json()["id"] == str(document_id)
    assert response.json()["filename"] == "test.pdf"
    assert response.json()["status"] == "pending"
    assert response.json()["total_pages"] == 5

def test_process_document_endpoint(client: TestClient, session: Session):
    """Test the process document endpoint."""
    # Create a test document
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        filename="test.pdf",
        file_size=1024,
        status=ProcessingStatus.PENDING,
        total_pages=5
    )
    session.add(document)
    session.commit()
    
    # Mock the task queue
    with patch("app.worker.enqueue_process_document") as mock_enqueue:
        mock_enqueue.return_value = AsyncMock()
        
        # Call the endpoint
        response = client.post(f"/handwriting/documents/{document_id}/process")
        
        assert response.status_code == 200
        assert response.json()["document_id"] == str(document_id)
        assert response.json()["status"] == "processing_queued"
        
        # Check if the task was enqueued
        mock_enqueue.assert_called_once_with(document_id, None)

def test_get_job_status_endpoint(client: TestClient, session: Session):
    """Test the get job status endpoint."""
    # Create a test document and job
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        filename="test.pdf",
        file_size=1024,
        status=ProcessingStatus.PROCESSING,
        total_pages=5
    )
    session.add(document)
    
    job_id = uuid.uuid4()
    job = ExtractionJob(
        id=job_id,
        document_id=document_id,
        status=ProcessingStatus.PROCESSING,
        pages_processed=2,
        total_pages=5,
        model_name="gpt-4.1"
    )
    session.add(job)
    session.commit()
    
    # Call the endpoint
    response = client.get(f"/handwriting/jobs/{job_id}")
    
    assert response.status_code == 200
    assert response.json()["id"] == str(job_id)
    assert response.json()["document_id"] == str(document_id)
    assert response.json()["status"] == "processing"
    assert response.json()["pages_processed"] == 2
    assert response.json()["total_pages"] == 5
    assert response.json()["model_name"] == "gpt-4.1" 