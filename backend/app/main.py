from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.e2e_socket import router as e2e_socket_router
from app.api.routes.session_socket import router as session_socket_router
from app.clients.mongodb import MongoDBClient
from app.clients.minio import MinioClient
from app.config import load_settings, Settings

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


def get_mongodb(request: Request) -> MongoDBClient:
    """Dependency injection for MongoDB client."""
    return request.app.state.mongodb


def get_minio(request: Request) -> MinioClient:
    """Dependency injection for MinIO client."""
    return request.app.state.minio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Load settings
    settings: Settings = load_settings()
    app.state.settings = settings

    # Initialize MongoDB client
    mongo_connection_string = f"mongodb://{settings.mongo_host}:{settings.mongo_port}"
    app.state.mongodb = MongoDBClient(
        connection_string=mongo_connection_string,
        database=settings.mongo_db,
    )
    # Ensure MongoDB connection is established
    _ = await app.state.mongodb.db

    # Initialize MinIO client (optional - may fail if MinIO not available)
    try:
        app.state.minio = MinioClient(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            public_endpoint=settings.minio_public_endpoint,
        )
        # Ensure bucket exists
        await app.state.minio.initialize()
    except Exception:
        # MinIO is optional - log warning and continue
        app.state.minio = None

    app.state.lifespan_started = True
    yield
    app.state.lifespan_shutdown = True

    # Shutdown: Close clients
    if hasattr(app.state, 'mongodb') and app.state.mongodb:
        await app.state.mongodb.close()


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
app.include_router(e2e_socket_router)
