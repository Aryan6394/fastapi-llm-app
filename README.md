# FastAPI LLM Streaming Microservice

A production-oriented, Dockerized FastAPI microservice that streams responses from Google Gemini over Server-Sent Events (SSE), complete with API key authentication, in-memory TTL prompt caching, reverse-proxy-aware rate limiting, automatic model fallback, and a built-in browser chat UI.

## Live Deployment

* **Browser Chat UI:** [https://fastapi-llm-app-5z87.onrender.com/](https://fastapi-llm-app-5z87.onrender.com/)
* **Interactive Swagger Docs:** [https://fastapi-llm-app-5z87.onrender.com/docs](https://fastapi-llm-app-5z87.onrender.com/docs)
* **Health Check:** [https://fastapi-llm-app-5z87.onrender.com/health](https://fastapi-llm-app-5z87.onrender.com/health)
* **Streaming Endpoint:** `POST https://fastapi-llm-app-5z87.onrender.com/api/v1/chat/stream`

*(Note: Hosted on Render Free Tier; the first request after an idle period may take ~50 seconds for container cold start.)*

---

## Key Features

* **Real-Time SSE Token Streaming:** Streams tokens asynchronously from the `google-genai` SDK using `text/event-stream`. Chunks are JSON-encoded (`data: "<token>"`) so multiline Markdown, bullet lists, and code blocks render intact without SSE newline splitting.
* **Automatic & Sticky Model Fallback:** Defaults to `gemini-3.8-flash` and automatically discovers and switches to available Gemini Flash text models if the primary model returns transient `503 UNAVAILABLE`, `429`, or `404` errors—remembering the healthy active model for subsequent requests.
* **In-Memory TTL Prompt Caching (`cachetools`):** Normalizes prompts (`strip().lower()`) and caches up to **100 unique prompts for 10 minutes (600s)** in RAM without requiring an external Redis instance. Exposes cache status via the `X-Cache: HIT | MISS` response header.
* **Reverse-Proxy-Aware Rate Limiting (`slowapi`):** Enforces **5 requests per minute** per `X-API-Key` (with `CF-Connecting-IP` and `X-Forwarded-For` client IP fallback behind Cloudflare/Render load balancers), returning `429 Too Many Requests` when exceeded.
* **API Key Authentication:** Protects `/api/v1/chat/stream` via the `X-API-Key` header, rejecting missing or invalid keys with `403 Forbidden`.
* **Zero-Dependency Browser Chat UI:** Serves a single-file dark-mode chat interface at `/` with live token rendering, response latency tracking, and `X-Cache` badge display.

---

## Project Structure

```text
fastapi-llm-app/
├── app/
│   ├── api/
│   │   └── chat.py          # POST /chat/stream endpoint, rate limit & X-Cache headers
│   ├── core/
│   │   ├── config.py        # Pydantic BaseSettings environment configuration
│   │   ├── limiter.py       # slowapi limiter keyed by X-API-Key / proxy client IP
│   │   └── security.py      # X-API-Key validation dependency
│   ├── services/
│   │   └── llm_service.py   # Async Gemini streaming, sticky fallback & TTLCache
│   ├── static/
│   │   └── index.html       # Single-file SSE browser chat frontend
│   └── main.py              # FastAPI app, CORS, root UI route & exception handlers
├── Dockerfile
├── requirements.txt
├── .gitignore
└── README.md