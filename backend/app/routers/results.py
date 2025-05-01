from fastapi import APIRouter, Request

router = APIRouter(prefix="/results", tags=["extraction"])


@router.get("/")
async def get_results(request: Request):
    return request.app.state.jobs  # type: ignore 