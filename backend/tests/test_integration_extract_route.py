from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ExtractionResult, LabRow


@pytest.fixture
def client():
    return TestClient(app)


def test_extract_route_s3_upload(monkeypatch, client):
    # Mock extract() to return deterministic result
    fake_result = ExtractionResult(
        sheet_name="sheet1",
        rows=[LabRow(sample_id="A1", measurement=1.0, unit="mg/L")],
    )
    from app.services import extract as extract_svc

    monkeypatch.setattr(extract_svc, "extract", lambda _bytes: fake_result)

    # Capture put_object calls
    uploaded_keys = []

    class FakeS3:
        def put_object(self, **kwargs):
            uploaded_keys.append(kwargs["Key"])

    from app.routers import extract as extract_router

    monkeypatch.setattr(extract_router, "get_s3_client", lambda: FakeS3())

    resp = client.post(
        "/extract/",
        files={"file": ("dummy.pdf", BytesIO(b"%PDF-1.4\n"), "application/pdf")},
    )

    assert resp.status_code == 201
    # Expect two uploads: json and xlsx
    assert len(uploaded_keys) == 2
    assert uploaded_keys[0].endswith(".json")
    assert uploaded_keys[1].endswith(".xlsx") 