from fastapi import FastAPI

app = FastAPI(title="DocTranscribe API", version="0.1.0")


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"} 