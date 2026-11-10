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


# body of POST /summarize: which sources to summarize (None = all ready ones) and whether to ignore the cache
class SummarizeRequest(BaseModel):
    source_ids: list[str] | None = None
    refresh: bool = False

# response of POST /summarize: the summary text with [file, p. N] citations
class SummarizeResponse(BaseModel):
    summary: str

class Cell(BaseModel):
    value: str | None = None
    page: int | None = None
    evidence: str | None = None

class ExtractRequest(BaseModel):
    source_ids: list[str] | None = None
    features: list[str] = Field(min_length=1)

class ExtractRow(BaseModel):
    source: str
    cells: dict[str, Cell]

class ExtractResponse(BaseModel):
    features: list[str]
    rows: list[ExtractRow]