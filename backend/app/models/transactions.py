"""Customers, vendors, income and expense entries (friendly fronts to journal entries)."""
from datetime import date

from sqlalchemy import String, ForeignKey, Numeric, Date, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin

PAYMENT_METHODS = {"cash", "check", "credit_card", "ach", "zelle", "venmo"}


class Customer(Base, IdMixin, TimestampMixin):
    __tablename__ = "customer"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Vendor(Base, IdMixin, TimestampMixin):
    __tablename__ = "vendor"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    is_1099: Mapped[bool] = mapped_column(Boolean, default=False)
    tin_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Income(Base, IdMixin, TimestampMixin):
    __tablename__ = "income"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    customer_id: Mapped[str | None] = mapped_column(
        ForeignKey("customer.id"), nullable=True
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    payment_method: Mapped[str] = mapped_column(String(20))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    deposit_account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    sales_tax_collected: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    journal_entry_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Expense(Base, IdMixin, TimestampMixin):
    __tablename__ = "expense"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    vendor_id: Mapped[str | None] = mapped_column(ForeignKey("vendor.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    payment_method: Mapped[str] = mapped_column(String(20))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    paid_from_account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    business_purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    reimbursable: Mapped[bool] = mapped_column(Boolean, default=False)
    tax_deductible: Mapped[bool] = mapped_column(Boolean, default=True)
    cpa_review: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    journal_entry_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
