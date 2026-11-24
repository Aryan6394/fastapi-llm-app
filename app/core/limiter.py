from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limit_key(request: Request) -> str:
    """Rate-limit by X-API-Key first so reverse-proxy IPs never split buckets."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{api_key.strip()}"

    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return f"ip:{cf_ip.strip()}"

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_rate_limit_key)