from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
