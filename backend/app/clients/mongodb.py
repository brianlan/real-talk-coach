from __future__ import annotations

from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection


class MongoDBClient:
    """Async MongoDB client with connection pooling.
    
    Uses PyMongo Async (AsyncIOMotorClient) with configurable connection pooling.
    
    Example:
        async with MongoDBClient("mongodb://localhost:27017", "mydb") as client:
            collection = client.collection("users")
            await collection.insert_one({"name": "Alice"})
    """

    def __init__(
        self,
        connection_string: str,
        database: str,
        *,
        max_pool_size: int = 50,
        min_pool_size: int = 10,
    ) -> None:
        """Initialize the MongoDB client.
        
        Args:
            connection_string: MongoDB connection URI (e.g., "mongodb://localhost:27017")
            database: Name of the database to connect to
            max_pool_size: Maximum number of connections in the pool (default: 50)
            min_pool_size: Minimum number of connections in the pool (default: 10)
        """
        self._connection_string = connection_string
        self._database_name = database
        self._max_pool_size = max_pool_size
        self._min_pool_size = min_pool_size
        
        self._client: AsyncMongoClient | None = None
        self._db: AsyncDatabase | None = None

    async def _ensure_connected(self) -> None:
        """Ensure the client is connected."""
        if self._client is None:
            self._client = AsyncMongoClient(
                self._connection_string,
                maxPoolSize=self._max_pool_size,
                minPoolSize=self._min_pool_size,
            )
            self._db = self._client[self._database_name]

    @property
    async def db(self) -> AsyncDatabase:
        """Get the database accessor.
        
        Returns:
            AsyncDatabase: The configured database instance
        """
        await self._ensure_connected()
        return self._db  # type: ignore

    async def collection(self, name: str) -> AsyncCollection:
        """Get a collection accessor.
        
        Args:
            name: Name of the collection
            
        Returns:
            AsyncIOMotorCollection: The collection instance
        """
        database = await self.db
        return database[name]

    async def create_index(
        self,
        collection_name: str,
        keys: str | list[tuple[str, Any]],
        *,
        unique: bool = False,
        background: bool = True,
        name: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Create an index on a collection.
        
        Args:
            collection_name: Name of the collection
            keys: Field(s) to index. Can be a single field name or list of (field, direction) tuples.
                  Direction: 1 (ascending), -1 (descending), "2d", "2dsphere", "text", "hashed"
            unique: Whether the index should enforce uniqueness (default: False)
            background: Build index in the background (default: True)
            name: Optional custom index name
            **kwargs: Additional index options passed to create_index
            
        Returns:
            str: The name of the created index
        """
        collection = await self.collection(collection_name)
        
        index_options: dict[str, Any] = {
            "background": background,
        }
        if unique:
            index_options["unique"] = unique
        if name:
            index_options["name"] = name
        index_options.update(kwargs)
        
        return await collection.create_index(keys, **index_options)

    async def close(self) -> None:
        """Close the client connection and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._db = None

    async def __aenter__(self) -> "MongoDBClient":
        """Enter async context manager."""
        await self._ensure_connected()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager and close connection."""
        await self.close()
