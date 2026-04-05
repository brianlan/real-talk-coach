import httpx
import mongomock
import pytest

from app.clients.llm import EvaluatorClient, QwenClient


@pytest.fixture(autouse=True)
def _setup_app_state(monkeypatch):
    """Set up app state with MongoDB client for tests."""
    import os
    from app.main import app
    from app.clients.mongodb import MongoDBClient
    
    # Set up MongoDB client in app.state
    client = MongoDBClient(
        connection_string=f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:{os.getenv('MONGO_PORT', '27017')}",
        database=os.getenv('MONGO_DB', 'test_db'),
    )
    app.state.mongodb = client
    app.state.minio = None
    app.state.lifespan_started = True


@pytest.fixture(autouse=True)
def _set_default_env(monkeypatch):
    monkeypatch.setenv("MONGO_HOST", "localhost")
    monkeypatch.setenv("MONGO_PORT", "27017")
    monkeypatch.setenv("MONGO_DB", "real-talk-coach")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET", "audio")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "secret")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "admin-token")
    # Volcengine RTC env vars
    monkeypatch.setenv("VOLCENGINE_ACCESS_KEY_ID", "ak-test")
    monkeypatch.setenv("VOLCENGINE_SECRET_ACCESS_KEY", "sk-test")
    monkeypatch.setenv("VOLCENGINE_RTC_APP_ID", "app-test")
    monkeypatch.setenv("VOLCENGINE_RTC_APP_KEY", "app-key-test")
    monkeypatch.setenv("VOLCENGINE_VOICE_CHAT_ENDPOINT", "https://rtc.volcengineapi.com")
    monkeypatch.setenv("VOLCENGINE_VOICE_MODEL_ID", "doubao-voice-realtime")
    monkeypatch.setenv("VOLCENGINE_CALLBACK_SIGNATURE", "test-callback-secret-key")
    monkeypatch.setenv("VOLCENGINE_VOICE_MODEL_ID", "doubao-voice-realtime")


@pytest.fixture
def mongomock_client():
    """Provide an in-memory MongoDB client using mongomock.
    
    This fixture creates a mock MongoDB client that can be used in tests
    instead of requiring a real MongoDB instance. The client is cleaned
    up after each test.
    
    Yields:
        mongomock.MongoClient: An in-memory MongoDB client
    """
    client = mongomock.MongoClient()
    yield client
    client.close()


@pytest.fixture
def mongomock_db(mongomock_client):
    """Provide an in-memory MongoDB database.
    
    This fixture creates a test database within the mongomock client.
    
    Args:
        mongomock_client: The mongomock client fixture
        
    Yields:
        mongomock.Database: An in-memory test database
    """
    db = mongomock_client["test_db"]
    yield db


@pytest.fixture
def mongomock_client_fixture():
    """Provide an async-compatible MongoDB mock client for tests.
    
    This fixture creates a that can be used mock MongoDB client in tests
    instead of requiring a real MongoDB instance.
    
    Yields:
        A mock MongoDB client with db property
    """
    client = mongomock.MongoClient()
    
    class MockMongoDBClient:
        def __init__(self, _client):
            self._client = _client
            self._db = _client["test_db"]
        
        @property
        async def db(self):
            return self._db
            
        async def collection(self, name):
            return self._db[name]
            
        async def close(self):
            self._client.close()
    
    yield MockMongoDBClient(client)


@pytest.fixture
async def qwen_client():
    async def handler(request):
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        return httpx.Response(200, json={"text": "ok"})

    transport = httpx.MockTransport(handler)
    client = QwenClient(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="secret",
        transport=transport,
    )
    yield client
    await client.close()


@pytest.fixture
async def evaluator_client():
    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = httpx.MockTransport(handler)
    client = EvaluatorClient(
        base_url="https://api.chataiapi.com/v1",
        api_key="secret",
        transport=transport,
    )
    yield client
    await client.close()
