# FastAPI LLM Streaming Microservice

A production-ready, Dockerized FastAPI microservice that streams responses from Google Gemini over Server-Sent Events (SSE), complete with API key authentication, in-memory TTL prompt caching, reverse-proxy-aware rate limiting, automatic model fallback, and a built-in browser chat UI.

## Live Deployment

* **Browser Chat UI:** https://fastapi-llm-app-5z87.onrender.com/
* **Interactive Swagger Docs:** https://fastapi-llm-app-5z87.onrender.com/docs
* **Health Check:** https://fastapi-llm-app-5z87.onrender.com/health
* **Streaming Endpoint:** `POST https://fastapi-llm-app-5z87.onrender.com/api/v1/chat/stream`

> **Note:** Hosted on Render Free Tier. The first request after an idle period may take ~50 seconds while the container spins up.

---

## Architecture & Request Flow

```text
Client (Browser Chat UI / curl / Python)
   │
   ▼
[1] FastAPI + CORS Middleware
   │
   ▼
[2] X-API-Key Authentication ──► 403 Forbidden (Missing/Invalid Key)
   │
   ▼
[3] slowapi Rate Limiter ──────► 429 Too Many Requests (> 5 req/min)
   │   (Keyed by X-API-Key, fallback to CF-Connecting-IP / X-Forwarded-For)
   ▼
[4] cachetools TTLCache ───────► 200 OK + X-Cache: HIT (Instant SSE Stream)
   │   (Max 100 normalized prompts, 10-minute TTL)
   ▼
[5] Google GenAI Async Stream ─► 200 OK + X-Cache: MISS (Live Token SSE Stream)
       (Primary: gemini-3.8-flash + Sticky Fallback across active Flash models)
```

---

## Key Features

* **Real-Time SSE Token Streaming:** Streams tokens asynchronously from the `google-genai` SDK over `text/event-stream`. Each chunk is JSON-encoded (`data: "<token>"`) so multiline Markdown, bullet lists, and code blocks render intact without SSE newline splitting, ending cleanly with `data: [DONE]`.
* **Automatic & Sticky Model Fallback:** Defaults to `gemini-3.8-flash` and automatically discovers and switches to other active Gemini Flash text models if the primary model hits transient `503 UNAVAILABLE`, `429`, or `404` errors—persisting the healthy active model for subsequent requests.
* **In-Memory TTL Prompt Caching (`cachetools`):** Normalizes prompts (`strip().lower()`) and caches up to **100 unique prompts for 10 minutes (`ttl=600`)** in RAM without requiring an external Redis server. Exposes cache status via the `X-Cache: HIT | MISS` response header.
* **Reverse-Proxy-Aware Rate Limiting (`slowapi`):** Enforces **5 requests per minute** keyed primarily by `X-API-Key` (with `CF-Connecting-IP` and `X-Forwarded-For` client IP fallback behind Cloudflare/Render proxies), returning `429 Too Many Requests` when exceeded.
* **API Key Authentication:** Secures `/api/v1/chat/stream` via the `X-API-Key` header, rejecting unauthorized callers with `403 Forbidden`.
* **Zero-Dependency Browser Chat UI:** Serves a single-file dark-mode chat interface at `GET /` with live token streaming, elapsed latency tracking, and `X-Cache` badge display.

---

## Tech Stack

* **Framework:** FastAPI, Uvicorn, Pydantic Settings
* **LLM SDK:** Google GenAI SDK (`google-genai`)
* **Caching & Rate Limiting:** `cachetools`, `slowapi`
* **Frontend:** Vanilla HTML5, CSS3, Fetch Streams API
* **Container & Hosting:** Docker, GitHub CI/CD, Render

---

## Project Structure

```text
fastapi-llm-app/
├── app/
│   ├── api/
│   │   └── chat.py          # POST /chat/stream route, rate limit & X-Cache headers
│   ├── core/
│   │   ├── config.py        # Pydantic BaseSettings environment configuration
│   │   ├── limiter.py       # slowapi limiter keyed by X-API-Key / proxy client IP
│   │   └── security.py      # X-API-Key header validation dependency
│   ├── services/
│   │   └── llm_service.py   # Async Gemini streaming, sticky fallback & TTLCache
│   ├── static/
│   │   └── index.html       # Single-file SSE browser chat UI served at /
│   └── main.py              # FastAPI app, CORS, root UI route & exception handlers
├── Dockerfile
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Environment Variables

Create a `.env` file in the project root (excluded from Git via `.gitignore`) or configure these variables in your Render dashboard:

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `API_KEY` | Yes | Secret key required in the `X-API-Key` request header | `your-custom-secret-key` |
| `GEMINI_API_KEY` | Yes | Google AI Studio API key for Gemini | `AIzaSy...` |
| `PORT` | No | Server port (defaults to `8080` in Docker/Render) | `8080` |

---

## Running Locally

### Option 1: Python Virtual Environment

```bash
git clone [https://github.com/Aryan6394/fastapi-llm-app.git](https://github.com/Aryan6394/fastapi-llm-app.git)
cd fastapi-llm-app

python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Open `http://localhost:8080/` for the Chat UI or `http://localhost:8080/docs` for Swagger UI.

### Option 2: Docker

```bash
docker build -t fastapi-llm-app .
docker run -p 8080:8080 --env-file .env fastapi-llm-app
```

---

## API Reference

### `POST /api/v1/chat/stream`

Streams a Gemini completion for a given text prompt.

* **Headers:**
  * `Content-Type: application/json`
  * `X-API-Key: <API_KEY>`
* **Request Body:**
  ```json
  {
    "prompt": "Explain Server-Sent Events in 3 bullet points."
  }
  ```
* **Response Headers:**
  * `Content-Type: text/event-stream; charset=utf-8`
  * `X-Cache: MISS` (fresh generation) or `X-Cache: HIT` (served from memory cache)
* **Response Codes:**
  * `200 OK` — Active SSE token stream (`data: "<chunk>"` ... `data: [DONE]`)
  * `403 Forbidden` — Missing or invalid `X-API-Key`
  * `422 Unprocessable Entity` — Invalid JSON payload
  * `429 Too Many Requests` — Rate limit (`5 per 1 minute`) exceeded

### `GET /health`

Returns service health status (`200 OK`):

```json
{
  "status": "healthy",
  "service": "FastAPI LLM Microservice"
}
```

---

## API Usage Examples

### 1. `curl` (Terminal)

```bash
curl -N -X POST "[https://fastapi-llm-app-5z87.onrender.com/api/v1/chat/stream](https://fastapi-llm-app-5z87.onrender.com/api/v1/chat/stream)" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"prompt": "Explain Server-Sent Events in 3 bullet points."}'
```

### 2. Python (`httpx`)

```python
import json
import httpx

url = "[https://fastapi-llm-app-5z87.onrender.com/api/v1/chat/stream](https://fastapi-llm-app-5z87.onrender.com/api/v1/chat/stream)"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "YOUR_API_KEY",
}
payload = {"prompt": "Explain Server-Sent Events in 3 bullet points."}

with httpx.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
    print("Status:", response.status_code)
    print("X-Cache:", response.headers.get("x-cache"))

    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        raw = line[6:]
        if raw == "[DONE]":
            break
        print(json.loads(raw), end="", flush=True)
```