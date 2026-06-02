"""Users and their per-company access."""
from datetime import datetime

from sqlalchemy import String, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin

ROLES = {"owner", "admin", "bookkeeper", "payroll", "cpa_readonly"}


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserCompany(Base, IdMixin, TimestampMixin):
    """Grants a user access to a company with a role. Supports husband + wife + CPA."""
    __tablename__ = "user_company"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"))
    role: Mapped[str] = mapped_column(String(20), default="owner")
