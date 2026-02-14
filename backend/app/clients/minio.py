from __future__ import annotations

import asyncio
from dataclasses import dataclass
from io import BytesIO


from minio import Minio
from minio.error import S3Error


@dataclass
class MinioError(Exception):
    """Exception for MinIO client errors."""

    message: str
    status_code: int | None = None
    body: str | None = None

    def __str__(self) -> str:
        return self.message


class MinioClient:
    """Async MinIO client for S3-compatible file storage."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
        region: str | None = None,
    ) -> None:
        """Initialize the MinIO client and ensure bucket exists.

        Args:
            endpoint: MinIO server endpoint (e.g., 'localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket: Bucket name to use
            secure: Whether to use HTTPS (default: False)
            region: Optional region for the bucket
        """
        self._bucket = bucket
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )
        self._loop = asyncio.get_event_loop()

    async def _ensure_bucket(self) -> None:
        """Ensure the bucket exists, creating it if necessary."""
        try:
            exists = await asyncio.to_thread(
                self._client.bucket_exists, self._bucket
            )
            if not exists:
                await asyncio.to_thread(
                    self._client.make_bucket, self._bucket
                )
        except S3Error as exc:
            raise MinioError(
                f"Failed to ensure bucket exists: {exc.message}",
                status_code=exc.code,
            ) from exc

    async def initialize(self) -> None:
        """Initialize the client - call this after creating the client."""
        await self._ensure_bucket()

    async def upload_file(
        self, name: str, data: bytes, content_type: str
    ) -> str:
        """Upload a file to MinIO.

        Args:
            name: Object name (key) for the file
            data: File content as bytes
            content_type: MIME type of the file (e.g., 'audio/wav')

        Returns:
            The object name that was uploaded

        Raises:
            MinioError: If upload fails
        """
        data_stream = BytesIO(data)
        try:
            await asyncio.to_thread(
                self._client.put_object,
                self._bucket,
                name,
                data_stream,
                len(data),
                content_type=content_type,
            )
            return name
        except S3Error as exc:
            raise MinioError(
                f"Failed to upload file: {exc.message}",
                status_code=exc.code,
            ) from exc

    async def download_file(self, name: str) -> bytes:
        """Download a file from MinIO.

        Args:
            name: Object name (key) to download

        Returns:
            File content as bytes

        Raises:
            MinioError: If download fails or object not found
        """
        try:
            response = await asyncio.to_thread(
                self._client.get_object, self._bucket, name
            )
            data = response.read()
            response.close()
            return data
        except S3Error as exc:
            raise MinioError(
                f"Failed to download file: {exc.message}",
                status_code=exc.code,
            ) from exc

    async def get_signed_url(
        self, name: str, expires: int = 900
    ) -> str:
        """Generate a presigned GET URL for an object.

        Args:
            name: Object name (key)
            expires: URL expiration time in seconds (default: 900 = 15 minutes)

        Returns:
            Presigned URL string

        Raises:
            MinioError: If URL generation fails
        """
        try:
            # Convert expires seconds to timedelta
            from datetime import timedelta
            expires_delta = timedelta(seconds=expires)
            url = await asyncio.to_thread(
                self._client.presigned_get_object,
                self._bucket,
                name,
                expires_delta,
            )
            return url
        except S3Error as exc:
            raise MinioError(
                f"Failed to generate signed URL: {exc.message}",
                status_code=exc.code,
            ) from exc

    async def delete_file(self, name: str) -> None:
        """Delete a file from MinIO.

        Args:
            name: Object name (key) to delete

        Raises:
            MinioError: If deletion fails
        """
        try:
            await asyncio.to_thread(
                self._client.remove_object, self._bucket, name
            )
        except S3Error as exc:
            raise MinioError(
                f"Failed to delete file: {exc.message}",
                status_code=exc.code,
            ) from exc

    async def file_exists(self, name: str) -> bool:
        """Check if a file exists in the bucket.

        Args:
            name: Object name (key) to check

        Returns:
            True if file exists, False otherwise

        Raises:
            MinioError: If check fails
        """
        try:
            await asyncio.to_thread(
                self._client.stat_object, self._bucket, name
            )
            return True
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return False
            raise MinioError(
                f"Failed to check file existence: {exc.message}",
                status_code=exc.code,
            ) from exc
