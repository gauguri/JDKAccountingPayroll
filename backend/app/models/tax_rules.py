"""Versioned, effective-dated tax rules. The heart of payroll/tax compliance.

NOTHING in business logic hardcodes a rate. Services ask this table for a value
and record the ruleset version used, so any calculation is reproducible and a
human approves rates before they can be used in a real payroll.
"""
from datetime import date

from sqlalchemy import String, ForeignKey, Date, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin

# status: only 'approved' rulesets may be used to run a real payroll.
RULESET_STATUS = {"draft", "under_review", "approved", "retired"}
TAX_TYPES = {
    "ss", "medicare", "addl_medicare", "futa", "suta",
    "fed_withholding", "state_withholding",
}


class TaxRuleset(Base, IdMixin, TimestampMixin):
    __tablename__ = "tax_ruleset"

    jurisdiction: Mapped[str] = mapped_column(String(8))   # US, NJ, NY, ...
    tax_type: Mapped[str] = mapped_column(String(24))
    tax_year: Mapped[int] = mapped_column()
    version: Mapped[int] = mapped_column(default=1)
    effective_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    source_citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    rules: Mapped[list["TaxRule"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )


class TaxRule(Base, IdMixin):
    __tablename__ = "tax_rule"

    ruleset_id: Mapped[str] = mapped_column(ForeignKey("tax_ruleset.id"), index=True)
    key: Mapped[str] = mapped_column(String(60))      # e.g. "rate", "wage_base", "brackets"
    value_num: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    value_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    ruleset: Mapped[TaxRuleset] = relationship(back_populates="rules")
