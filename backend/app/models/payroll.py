"""Payroll: employees, employer setup, runs, line items, pay stubs."""
from datetime import date

from sqlalchemy import String, ForeignKey, Numeric, Date, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin

PAY_TYPES = {"hourly", "salary"}
FILING_STATUSES = {"single", "married_joint", "married_separate", "head_of_household"}
RUN_STATUS = {"draft", "calculated", "approved", "posted"}


class Employee(Base, IdMixin, TimestampMixin):
    __tablename__ = "employee"

    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ssn_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pay_type: Mapped[str] = mapped_column(String(10), default="hourly")
    pay_rate: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # /hr or /year
    filing_status: Mapped[str] = mapped_column(String(20), default="single")
    fed_allowances: Mapped[int] = mapped_column(Integer, default=0)
    fed_extra_withholding: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    state_extra_withholding: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    dd_info_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EmployerPayrollSetup(Base, IdMixin, TimestampMixin):
    __tablename__ = "employer_payroll_setup"

    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), unique=True, index=True)
    state_employer_id_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payroll_schedule: Mapped[str] = mapped_column(String(20), default="biweekly")
    suta_rate: Mapped[float] = mapped_column(Numeric(9, 6), default=0)
    local_tax_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class PayrollRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "payroll_run"

    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    pay_period_start: Mapped[date] = mapped_column(Date)
    pay_period_end: Mapped[date] = mapped_column(Date)
    pay_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    journal_entry_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # which approved/draft rulesets were used, for traceability
    tax_versions_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["PayrollItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class PayrollItem(Base, IdMixin):
    __tablename__ = "payroll_item"

    payroll_run_id: Mapped[str] = mapped_column(ForeignKey("payroll_run.id"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employee.id"), index=True)
    hours: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    gross_pay: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    fed_wh: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    state_wh: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    ss_employee: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    medicare_employee: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    ss_employer: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    medicare_employer: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    futa: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    suta: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    net_pay: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    calc_explanation_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[PayrollRun] = relationship(back_populates="items")


class PayStub(Base, IdMixin, TimestampMixin):
    __tablename__ = "pay_stub"
    payroll_item_id: Mapped[str] = mapped_column(ForeignKey("payroll_item.id"), index=True)
    pdf_path: Mapped[str | None] = mapped_column(String(400), nullable=True)
