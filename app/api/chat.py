from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.core.chat import answer

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return answer(request.question, source_ids=request.source_ids, k=request.k)


