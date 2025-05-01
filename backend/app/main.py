from fastapi import FastAPI
from .routers import upload

app = FastAPI(title="DocTranscribe API", version="0.1.0")

app.include_router(upload.router)

@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"} 