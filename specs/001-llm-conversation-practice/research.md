# Research Notes

1. **Decision**: Use FastAPI 0.115 + Python 3.11 + Uvicorn workers for the backend, keeping async endpoints/WebSockets for turns and telemetry.  
   **Rationale**: Aligns with spec requirement, delivers excellent async performance for <20 concurrent sessions, integrates cleanly with httpx + ASGI lifespan hooks, and keeps deployment lightweight compared to heavier frameworks.  
   **Alternatives considered**: Django + Channels (more boilerplate, slower iteration); Node.js/Express (breaks requirement to leverage FastAPI contracts).

2. **Decision**: Store all structured data and audio references in LeanCloud via REST (LObject for Scenario/PracticeSession/Turn/Evaluation + LFile for MP3 blobs) using backend-side repositories.  
   **Rationale**: Matches existing contracts, keeps storage single-source-of-truth, and avoids introducing additional databases; LeanCloud SDK via httpx plus retries satisfies encryption and cascade delete requirements.  
   **Alternatives considered**: Self-hosted Postgres + S3 (deviates from spec + increases ops load); LeanCloud JS SDK on frontend (would expose credentials and break single-tenant stub).

3. **Decision**: Frontend built with Next.js 15 (App Router) + TypeScript + React Server Components, using Web Audio API for recording/playback and native WebSocket client for termination events.  
   **Rationale**: Gives SSR for scenario/history screens, good DX for bundling audio workers, and plays nicely with FastAPI WebSockets + fetch; Next.js 15 includes turbopack + server actions that simplify stub user scope.  
   **Alternatives considered**: Vite + React SPA (lighter but would require more manual routing/data-fetch wiring); Remix (less mature audio recording examples, smaller community).

4. **Decision**: Use FastAPI in-process background tasks for both evaluation and ASR, persisting status in LeanCloud but relying on the API process lifetime for retries.  
   **Rationale**: Satisfies MVP goals without provisioning additional worker infrastructure; acceptable tradeoff since durability can be handled manually (requeue) if a process restarts.  
   **Alternatives considered**: Celery + Redis (adds ops surface); dedicated LeanCloud polling worker (more moving parts for this MVP); fire-and-forget without status tracking (no visibility for UI).

5. **Finding**: Qwen3-omni-flash exposes an OpenAI-compatible streaming API via DashScope (`https://dashscope.aliyuncs.com/compatible-mode/v1`). Every request must set `stream=True`, `modalities=["text","audio"]`, and `audio={"voice": "<voiceId>", "format": "wav"}`; responses stream incremental text plus base64 audio data.
   **Implication**: Backend uses the OpenAI Python AsyncClient (≥1.52.0) for reliable streaming response handling. The client automatically handles Server-Sent Events (SSE) format and accumulates text and audio chunks. **Implementation Note**: Qwen returns raw PCM audio data (16-bit signed integer, 24kHz, mono) without WAV headers, not WAV format as initially planned. The backend detects audio format by checking for "RIFF" header and converts raw PCM to MP3 using ffmpeg with `-f s16le -ar 24000 -ac 1` flags. Audio is then uploaded to LeanCloud using `DASHSCOPE_API_KEY` for authentication.
   **Supported Voice IDs**: Cherry (recommended), Serena, Ethan, Chelsie for qwen3-omni-flash.  

6. **Finding**: The text-only evaluator will call GPT-5 mini hosted at `https://api.chataiapi.com/v1/chat/completions` with bearer `secretKey`, reusing OpenAI chat semantics (messages array, `model`, moderation metadata).  
   **Implication**: Evaluation tasks can use standard httpx/OpenAI client patterns, capture token usage from the response, and map the assistant message to rubric scores without building a bespoke protocol.
