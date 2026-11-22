from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.llm_service import generate_stream
from app.core.security import get_api_key

router = APIRouter()

class ChatRequest(BaseModel):
    prompt: str

@router.post("/chat/stream", dependencies=[Depends(get_api_key)])
async def stream_chat(request: ChatRequest):
    return StreamingResponse(
        generate_stream(request.prompt),
        media_type="text/event-stream"
    )