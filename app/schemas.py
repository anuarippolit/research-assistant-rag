from pydantic import BaseModel, Field 

#source_id: str, filename: str, file_type: str, status: str, error: str | None, created_at: str
class SourceOut(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    error: str | None = None
    created_at: str

class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    source_ids: list[str] | None = None
    k: int = Field(default=5, ge=1, le=20)

class SourceRef(BaseModel):
    filename: str
    page: int
    score: float

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
