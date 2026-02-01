from fastapi import Depends, Header, HTTPException, status

from app.config import load_settings


def require_admin_token(x_admin_token: str | None = Header(None)) -> None:
    settings = load_settings()
    if settings.admin_auth_disabled:
        return
    if x_admin_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin token",
        )
    if x_admin_token != settings.admin_access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


AdminAuth = Depends(require_admin_token)
