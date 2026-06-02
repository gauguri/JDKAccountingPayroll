"""Shared FastAPI dependencies: auth and company-access scoping."""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserCompany


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_company(company_id: str, user: User, db: Session) -> str:
    """Ensure the user may access this company; returns the company_id."""
    link = (
        db.query(UserCompany)
        .filter(UserCompany.user_id == user.id, UserCompany.company_id == company_id)
        .first()
    )
    if not link:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this company")
    return company_id
