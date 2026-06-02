"""Double-entry ledger: journal entries and their balanced lines."""
from datetime import date

from sqlalchemy import String, ForeignKey, Numeric, Date, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin

SOURCE_TYPES = {
    "income", "expense", "payroll", "bank", "sales_tax",
    "reconcile", "opening_balance", "import", "manual",
}


class JournalEntry(Base, IdMixin, TimestampMixin):
    __tablename__ = "journal_entry"

    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), default="manual")
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    posted: Mapped[bool] = mapped_column(Boolean, default=True)
    reversed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class JournalLine(Base, IdMixin):
    __tablename__ = "journal_line"

    journal_entry_id: Mapped[str] = mapped_column(
        ForeignKey("journal_entry.id"), index=True
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"), index=True)
    debit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    credit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
