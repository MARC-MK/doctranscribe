from fastapi import FastAPI
from .routers import upload, extract as extract_router, results as results_router

app = FastAPI(title="DocTranscribe API", version="0.1.0")
app.state.jobs = []  # store recent extraction jobs

app.include_router(upload.router)
app.include_router(extract_router.router)
app.include_router(results_router.router)

@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"} 