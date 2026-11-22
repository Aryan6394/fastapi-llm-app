from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.core.limiter import limiter
from app.core.security import get_api_key
from app.services.llm_service import generate_stream, is_prompt_cached

router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str


@router.post("/chat/stream", dependencies=[Depends(get_api_key)])
@limiter.limit("5/minute")
async def stream_chat(request: Request, payload: ChatRequest):
    cache_status = "HIT" if is_prompt_cached(payload.prompt) else "MISS"
    return StreamingResponse(
        generate_stream(payload.prompt),
        media_type="text/event-stream",
        headers={"X-Cache": cache_status},
    )