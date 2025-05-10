from fastapi import APIRouter, HTTPException, Request, status
from typing import List
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/jobs", tags=["jobs"])

# ---------- Models ----------

class Anomaly(BaseModel):
    row_id: str
    algorithm: str
    score: float
    dismissed: bool = False

class JobContext(BaseModel):
    json_file_id: str
    anomalies: List[Anomaly]
    xlsx_url: str

# ---------- Endpoints ----------

@router.get("/test", status_code=status.HTTP_200_OK)
async def test_jobs_router():
    """Simple test endpoint to check if the jobs router is working."""
    return {"status": "ok", "message": "Jobs router is working"}

@router.get("/{job_id}/context", response_model=JobContext)
async def get_job_context(job_id: str, request: Request):
    """Get context for a job, including anomalies and file references."""
    try:
        # In a real implementation, we would:
        # 1. Verify the job exists and belongs to the user
        # 2. Fetch the job details from the database
        # 3. Generate a presigned URL for the XLSX file
        # 4. Return the job context
        
        # For demonstration, return mock data
        return JobContext(
            json_file_id=f"file-{uuid.uuid4()}",
            anomalies=[
                Anomaly(
                    row_id="row-4",
                    algorithm="range_check",
                    score=0.98,
                    dismissed=False
                ),
                Anomaly(
                    row_id="row-7",
                    algorithm="statistical_outlier",
                    score=0.85,
                    dismissed=False
                )
            ],
            xlsx_url=f"https://example.com/{job_id}.xlsx"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching job context: {str(e)}"
        ) 