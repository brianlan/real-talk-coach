from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.session_socket import router as session_socket_router

CORS_ORIGINS = [
    "http://localhost:3000",
    "https://localhost:3443",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3443",
    "http://192.168.71.57:3000",
    "https://192.168.71.57:3443",
    "http://95.181.189.112:3000",
    "https://95.181.189.112:3443",
    "http://10.243.80.19:3000",
    "https://10.243.80.19:3443",
    "http://116.237.174.249:3000",
    "https://116.237.174.249:3443",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.lifespan_started = True
    yield
    app.state.lifespan_shutdown = True


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
app.include_router(session_socket_router)
