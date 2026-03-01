"""FastAPI dependencies for the application.

This module provides dependency injection functions for MongoDB and MinIO clients.
"""

from fastapi import Request

from app.clients.mongodb import MongoDBClient
from app.clients.minio import MinioClient


def get_mongodb_client(request: Request) -> MongoDBClient:
    """Dependency for MongoDB client from app state."""
    return request.app.state.mongodb


def get_minio_client(request: Request) -> MinioClient | None:
    """Dependency for MinIO client from app state."""
    return request.app.state.minio
