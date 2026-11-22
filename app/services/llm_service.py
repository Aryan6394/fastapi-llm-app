from google import genai
from app.core.config import settings

# Initialize the GenAI client with your API key
client = genai.Client(api_key=settings.GEMINI_API_KEY)

async def generate_stream(prompt: str):
    """
    Async generator that yields SSE (Server-Sent Events) formatted chunks.
    """
    response = await client.aio.models.generate_content_stream(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    async for chunk in response:
        if chunk.text:
            # SSE format requires "data: <content>\n\n"
            yield f"data: {chunk.text}\n\n"
            
    yield "data: [DONE]\n\n"