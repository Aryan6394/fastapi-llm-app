from fastapi import FastAPI
from app.core.config import settings
from app.api.chat import router as chat_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url=None,
)

# Attach the chat endpoints
app.include_router(chat_router, prefix=settings.API_V1_STR, tags=["Chat"])

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}