"""Chart of accounts."""
from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin

ACCOUNT_TYPES = {"income", "expense", "asset", "liability", "equity"}
# Normal balance by type: assets & expenses are debit-normal; the rest credit-normal.
NORMAL_BALANCE = {
    "asset": "debit",
    "expense": "debit",
    "income": "credit",
    "liability": "credit",
    "equity": "credit",
}


class Account(Base, IdMixin, TimestampMixin):
    __tablename__ = "account"

    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(20))
    subtype: Mapped[str | None] = mapped_column(String(40), nullable=True)
    description_plain: Mapped[str | None] = mapped_column(Text, nullable=True)
    normal_balance: Mapped[str] = mapped_column(String(6))  # debit|credit
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    # Preloaded accounts the user must not delete (can hide instead).
    system_locked: Mapped[bool] = mapped_column(Boolean, default=False)
