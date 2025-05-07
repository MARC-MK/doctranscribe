import io
import os
import subprocess
import time
from pathlib import Path

import boto3
import pytest
from fastapi.testclient import TestClient
import pathlib

from app.main import app
from app.config import settings as _settings


@pytest.fixture(scope="session", autouse=True)
def localstack_container():
    """Spin up LocalStack (S3) for the duration of test session."""
    # Ensure docker compose exists at project root
    root = Path(__file__).resolve().parents[2]
    subprocess.run(["docker", "compose", "-f", root / "docker-compose.yml", "up", "-d", "localstack"], check=True)
    # Wait for LocalStack to be ready
    time.sleep(5)
    yield
    subprocess.run(["docker", "compose", "-f", root / "docker-compose.yml", "rm", "-fsv", "localstack"], check=True)


@pytest.fixture(scope="session")
def s3_client():
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        endpoint_url="http://localhost:4566",
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_bucket(s3_client):
    s3_client.create_bucket(Bucket=_settings.s3_bucket)
    yield


def test_upload_pdf(s3_client, monkeypatch):
    # Override dependency to use test s3 client
    from app import deps

    monkeypatch.setattr(deps, "get_s3_client", lambda: s3_client)

    client = TestClient(app)

    pdf_path = pathlib.Path(__file__).parent / "fixtures" / "mental_health_survey_v4.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    response = client.post(
        "/upload/",
        files={"file": ("mental_health_survey_v4.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    print("RESPONSE:", response.status_code, response.text)

    assert response.status_code == 201
    data = response.json()

    # Ensure PDF metadata is present
    assert data["filename"] == "mental_health_survey_v4.pdf"
    assert data["filesize_bytes"] == len(pdf_bytes)
    assert data["page_count"] == 1  # This PDF has 1 page
    assert "mental_health_survey_v4.pdf" in data["summary"]
    assert "1 pages" in data["summary"]

    # Ensure object exists in S3 (by filename suffix)
    objects = s3_client.list_objects_v2(Bucket=_settings.s3_bucket)
    found = False
    for obj in objects.get("Contents", []):
        if obj["Key"].endswith("mental_health_survey_v4.pdf"):
            found = True
            break
    assert found, "Uploaded PDF not found in S3 bucket" 