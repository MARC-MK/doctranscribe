from fastapi import APIRouter, UploadFile, File, Depends, status
from ..services.extract import extract
from ..schemas import ExtractionResult

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.post("/", response_model=ExtractionResult, status_code=status.HTTP_201_CREATED)
async def extract_route(file: UploadFile = File(...)):
    result = extract(await file.read())
    return result 