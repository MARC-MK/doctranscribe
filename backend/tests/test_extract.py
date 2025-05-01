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
    # Simulate GPT failure, ensure Textract fallback path taken
    monkeypatch.setattr(svc, "call_gpt_4o", lambda _: (_ for _ in ()).throw(RuntimeError))
    monkeypatch.setattr(
        svc,
        "call_textract",
        lambda _: {"sheet_name": "fallback", "rows": []},
    )
    result = svc.extract(b"dummy")
    assert result.sheet_name == "fallback" 