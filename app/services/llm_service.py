from cachetools import TTLCache
from google import genai
from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Cache up to 100 unique prompts for 10 minutes (600 seconds)
prompt_cache: TTLCache = TTLCache(maxsize=100, ttl=600)


def normalize_prompt(prompt: str) -> str:
    return prompt.strip().lower()


def is_prompt_cached(prompt: str) -> bool:
    return normalize_prompt(prompt) in prompt_cache


async def generate_stream(prompt: str):
    """
    Async generator that yields SSE chunks, serving from TTL cache on repeat prompts.
    """
    cache_key = normalize_prompt(prompt)

    if cache_key in prompt_cache:
        yield f"data: {prompt_cache[cache_key]}\n\n"
        yield "data: [DONE]\n\n"
        return

    response = await client.aio.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    full_response = []
    async for chunk in response:
        if chunk.text:
            full_response.append(chunk.text)
            yield f"data: {chunk.text}\n\n"

    if full_response:
        prompt_cache[cache_key] = "".join(full_response)

    yield "data: [DONE]\n\n"