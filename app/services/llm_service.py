from cachetools import TTLCache
from google import genai
from google.genai.errors import APIError
from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Cache up to 100 unique prompts for 10 minutes (600 seconds)
prompt_cache: TTLCache = TTLCache(maxsize=100, ttl=600)

PRIMARY_MODEL = "gemini-3.8-flash"
EXCLUDED_KEYWORDS = ("image", "tts", "audio", "embedding", "robotics", "computer-use")


def normalize_prompt(prompt: str) -> str:
    return prompt.strip().lower()


def is_prompt_cached(prompt: str) -> bool:
    return normalize_prompt(prompt) in prompt_cache


async def get_fallback_flash_models(exclude_model: str) -> list[str]:
    """Dynamically discovers other available Gemini Flash text models on the API key."""
    fallbacks: list[str] = []
    try:
        pager = await client.aio.models.list()
        async for model in pager:
            name = (model.name or "").removeprefix("models/")
            actions = getattr(model, "supported_actions", None) or []
            lower_name = name.lower()
            if (
                name
                and name != exclude_model
                and "gemini" in lower_name
                and "flash" in lower_name
                and "generateContent" in actions
                and not any(bad in lower_name for bad in EXCLUDED_KEYWORDS)
            ):
                fallbacks.append(name)
    except Exception as exc:
        print(f"MODEL LIST WARNING: {type(exc).__name__}: {exc}", flush=True)
    return fallbacks


async def generate_stream(prompt: str):
    """
    Streams SSE chunks from Gemini with TTL caching and automatic fallback
    across available Flash models when the primary model returns 503/404.
    """
    cache_key = normalize_prompt(prompt)

    if cache_key in prompt_cache:
        yield f"data: {prompt_cache[cache_key]}\n\n"
        yield "data: [DONE]\n\n"
        return

    candidate_models = [PRIMARY_MODEL]
    last_error = None

    idx = 0
    while idx < len(candidate_models):
        model_name = candidate_models[idx]
        idx += 1
        full_response: list[str] = []

        try:
            response = await client.aio.models.generate_content_stream(
                model=model_name,
                contents=prompt,
            )

            async for chunk in response:
                if chunk.text:
                    full_response.append(chunk.text)
                    yield f"data: {chunk.text}\n\n"

            if full_response:
                prompt_cache[cache_key] = "".join(full_response)
                yield "data: [DONE]\n\n"
                return

        except APIError as exc:
            last_error = f"{type(exc).__name__} ({model_name}): {exc}"
            print(f"GEMINI STREAM RETRY: {last_error}", flush=True)
            # Only fall back if no tokens were sent yet and the error is transient/unavailable
            if not full_response and exc.code in (404, 429, 500, 503):
                if len(candidate_models) == 1:
                    candidate_models.extend(await get_fallback_flash_models(PRIMARY_MODEL))
                continue
            break

        except Exception as exc:
            last_error = f"{type(exc).__name__} ({model_name}): {exc}"
            print(f"GEMINI STREAM ERROR: {last_error}", flush=True)
            break

    yield f"data: [ERROR] {last_error or 'No response generated from Gemini.'}\n\n"
    yield "data: [DONE]\n\n"