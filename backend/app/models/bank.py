"""Bank CSV import and categorization."""
from datetime import date

from sqlalchemy import String, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin


class BankCsvMapping(Base, IdMixin, TimestampMixin):
    """Remembered column mapping per bank label."""
    __tablename__ = "bank_csv_mapping"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    bank_label: Mapped[str] = mapped_column(String(120))
    column_map: Mapped[str] = mapped_column(Text)  # JSON: {date, description, amount...}


class BankImportBatch(Base, IdMixin, TimestampMixin):
    __tablename__ = "bank_import_batch"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    bank_label: Mapped[str] = mapped_column(String(120))
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="preview")


class BankTransaction(Base, IdMixin, TimestampMixin):
    __tablename__ = "bank_transaction"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("bank_import_batch.id"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    direction: Mapped[str] = mapped_column(String(6))  # debit|credit
    status: Mapped[str] = mapped_column(String(15), default="unmatched")
    matched_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    matched_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dedupe_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)


class CategorizationRule(Base, IdMixin, TimestampMixin):
    __tablename__ = "categorization_rule"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    match_text: Mapped[str] = mapped_column(String(200))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    priority: Mapped[int] = mapped_column(Integer, default=100)
