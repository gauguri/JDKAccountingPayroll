"""Company, owners, bank-account nicknames, fiscal year, settings, CPA contact."""
from datetime import date

from sqlalchemy import String, ForeignKey, Numeric, Date, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin

BUSINESS_TYPES = {"sole_prop", "smllc", "partnership", "s_corp", "c_corp"}
PAYROLL_FREQUENCIES = {"weekly", "biweekly", "semimonthly", "monthly"}


class Company(Base, IdMixin, TimestampMixin):
    __tablename__ = "company"

    name: Mapped[str] = mapped_column(String(200))
    ein_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(2), default="NJ")
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    business_type: Mapped[str] = mapped_column(String(20), default="sole_prop")
    payroll_frequency: Mapped[str] = mapped_column(String(20), default="biweekly")
    tax_year: Mapped[int] = mapped_column(Integer, default=date.today().year)
    sales_tax_default_rate: Mapped[float] = mapped_column(
        Numeric(9, 6), default=0.06625  # NJ state sales tax
    )

    owners: Mapped[list["CompanyOwner"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    bank_accounts: Mapped[list["BankAccountName"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    fiscal_years: Mapped[list["FiscalYear"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    cpa_contacts: Mapped[list["CpaContact"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanyOwner(Base, IdMixin, TimestampMixin):
    __tablename__ = "company_owner"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"))
    name: Mapped[str] = mapped_column(String(200))
    ownership_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=100)
    is_signer: Mapped[bool] = mapped_column(Boolean, default=True)
    company: Mapped[Company] = relationship(back_populates="owners")


class BankAccountName(Base, IdMixin, TimestampMixin):
    __tablename__ = "bank_account_name"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"))
    label: Mapped[str] = mapped_column(String(120))
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    gl_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("account.id"), nullable=True
    )
    company: Mapped[Company] = relationship(back_populates="bank_accounts")


class FiscalYear(Base, IdMixin, TimestampMixin):
    __tablename__ = "fiscal_year"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"))
    year: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="open")  # open|closed
    company: Mapped[Company] = relationship(back_populates="fiscal_years")


class CpaContact(Base, IdMixin, TimestampMixin):
    __tablename__ = "cpa_contact"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"))
    name: Mapped[str] = mapped_column(String(200))
    firm: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[Company] = relationship(back_populates="cpa_contacts")


class Setting(Base, IdMixin, TimestampMixin):
    __tablename__ = "setting"
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"))
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
