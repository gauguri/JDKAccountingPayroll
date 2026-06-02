"""Registration, login, logout, current user."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import (
    hash_password, verify_password, create_access_token,
)
from app.models.user import User, UserCompany
from app.models.company import Company
from app.models.base import utcnow
from app.services.coa import seed_chart_of_accounts
from app.services import audit
from app.schemas import RegisterIn, LoginIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "access_token", token, httponly=True, samesite="lax",
        secure=settings.cookie_secure, max_age=settings.access_token_minutes * 60,
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    db.flush()

    company = Company(
        name=body.company_name, business_type=body.business_type, state=body.state,
    )
    db.add(company)
    db.flush()

    db.add(UserCompany(user_id=user.id, company_id=company.id, role="owner"))
    seed_chart_of_accounts(db, company.id)
    audit.record(
        db, company_id=company.id, user_id=user.id, action="create",
        entity_type="company", entity_id=company.id, after={"name": company.name},
    )
    db.commit()

    _set_cookie(response, create_access_token(user.id))
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    user.last_login_at = utcnow()
    db.commit()
    _set_cookie(response, create_access_token(user.id))
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
