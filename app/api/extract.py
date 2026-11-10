from fastapi import APIRouter, HTTPException

from app.core.extract import extract_table
from app.schemas import ExtractRequest, ExtractResponse

router = APIRouter()


# HTTP layer of extraction: ExtractRequest -> extract_table (search -> Claude -> Cell per source x feature) -> table
# plain `def`: the Claude calls block, so FastAPI runs it in the thread pool
@router.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest):
    try:
        return extract_table(request.source_ids, request.features)
    except ValueError as e:  # no sources / source not found
        raise HTTPException(status_code=400, detail=str(e))
