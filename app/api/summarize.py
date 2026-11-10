from fastapi import APIRouter, HTTPException

from app.core.summarize import summarize_all
from app.schemas import SummarizeRequest, SummarizeResponse

router = APIRouter()


# HTTP layer of the summary pipeline: SummarizeRequest -> summarize_all (cache -> chunks -> Claude) -> {"summary": ...}
# plain `def`: the Claude call blocks, so FastAPI runs it in the thread pool
@router.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest):
    try:
        text = summarize_all(request.source_ids, refresh=request.refresh)
    except ValueError as e:  # no sources / source not found / source not ready
        raise HTTPException(status_code=400, detail=str(e))
    return {"summary": text}
