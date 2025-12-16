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
