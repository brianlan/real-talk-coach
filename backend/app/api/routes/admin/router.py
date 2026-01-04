from fastapi import APIRouter, Depends

from app.api.deps.admin_auth import require_admin_token
from app.api.routes.admin.skills import router as skills_router
from app.api.routes.admin.scenarios import router as scenarios_router
from app.api.routes.admin.sessions import router as sessions_router
from app.api.routes.admin.audit_log import router as audit_log_router

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])

router.include_router(skills_router)
router.include_router(scenarios_router)
router.include_router(sessions_router)
router.include_router(audit_log_router)
