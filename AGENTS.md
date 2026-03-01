# real-talk-coach Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-14

## Active Technologies
- Backend Python 3.11 (FastAPI); Frontend TypeScript/Next.js 15 + FastAPI, Uvicorn, httpx, MongoDB, MinIO, qwen3-omni-flash, WebSockets, Next.js/React, Web Audio API (001-llm-conversation-practice)

- MongoDB for structured data storage (replaced LeanCloud)
- MinIO (S3-compatible) for audio file storage (replaced LeanCloud LFile)

## Project Structure

```text
backend/
frontend/
tests/
```

## Python Env

/Users/rlan/miniforge3/envs/mykik_py311/bin/python

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Backend Python 3.11 (FastAPI); Frontend TypeScript/Next.js 15: Follow standard conventions

## Mind your Proxy Settings

When encountering network issue accessing local IP and port, please try removing your proxy and try again.

## Recent Changes
- 002-admin-data-management: Added Backend Python 3.11 (FastAPI); Frontend TypeScript/Next.js 15 + FastAPI, Uvicorn, httpx, MongoDB, MinIO

- 001-llm-conversation-practice: Added Backend Python 3.11 (FastAPI); Frontend TypeScript/Next.js 15 + FastAPI, Uvicorn, httpx, WebSockets, MongoDB, MinIO, qwen3-omni-flash, Next.js/React, Web Audio API

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
