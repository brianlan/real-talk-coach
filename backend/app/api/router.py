from fastapi import APIRouter

from app.api.routes.scenarios import router as scenarios_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.turns import router as turns_router
from app.api.routes.session_socket import router as session_socket_router

api_router = APIRouter()
api_router.include_router(scenarios_router)
api_router.include_router(sessions_router)
api_router.include_router(turns_router)
api_router.include_router(session_socket_router)


@api_router.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
