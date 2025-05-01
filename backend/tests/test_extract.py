import pytest
from app.services import extract as svc
from app.schemas import ExtractionResult


def test_extract_valid(monkeypatch):
    # Force GPT success path
    fake_json = {
        "sheet_name": "sheet1",
        "rows": [
            {"sample_id": "A1", "measurement": 1.2, "unit": "mg/L"}
        ],
    }

    monkeypatch.setattr(svc, "call_gpt_4o", lambda _: fake_json)
    result = svc.extract(b"dummy")
    assert isinstance(result, ExtractionResult)
    assert result.sheet_name == "sheet1"


def test_extract_fallback(monkeypatch):
    # Mock S3 put_object to ensure it gets called
    put_called = {}
    monkeypatch.setattr(svc.boto3, "client", lambda *_args, **_kw: None)  # disable boto3 usage

    from app.routers import extract as extract_router

    def fake_put_object(**kwargs):
        put_called.update(kwargs)

    monkeypatch.setattr(extract_router, "get_s3_client", lambda: type("C", (), {"put_object": fake_put_object})())

    result = svc.extract(b"dummy")
    assert result.sheet_name == "fallback"
    assert "Body" in put_called 