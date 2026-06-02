"""Tax-rule lookups and the sample-2026 seed.

IMPORTANT: every rate here is SAMPLE DATA seeded in 'draft' status and must be
reviewed/approved by a CPA before it is used for a real payroll. The payroll
engine reads values from these rows and records the ruleset version used — it
never hardcodes a rate.
"""
import json
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tax_rules import TaxRuleset, TaxRule


def get_ruleset(db: Session, jurisdiction: str, tax_type: str, year: int,
                require_approved: bool = False) -> TaxRuleset | None:
    q = select(TaxRuleset).where(
        TaxRuleset.jurisdiction == jurisdiction,
        TaxRuleset.tax_type == tax_type,
        TaxRuleset.tax_year == year,
    )
    if require_approved:
        q = q.where(TaxRuleset.status == "approved")
    rulesets = db.execute(q).scalars().all()
    if not rulesets:
        return None
    return max(rulesets, key=lambda r: r.version)


def _rule(ruleset: TaxRuleset, key: str) -> TaxRule | None:
    for r in ruleset.rules:
        if r.key == key:
            return r
    return None


def get_num(ruleset: TaxRuleset, key: str, default=None) -> Decimal | None:
    r = _rule(ruleset, key)
    if r is None or r.value_num is None:
        return Decimal(str(default)) if default is not None else None
    return Decimal(str(r.value_num))


def get_json(ruleset: TaxRuleset, key: str, default=None):
    r = _rule(ruleset, key)
    if r is None or r.value_json is None:
        return default
    return json.loads(r.value_json)


# --------------------------------------------------------------------------
# Sample 2026 seed (DRAFT — review before use)
# --------------------------------------------------------------------------
SAMPLE_YEAR = 2026
_DISCLAIMER = "SAMPLE DATA seeded by JDK Books. Review and approve with your CPA before running real payroll."

# Simplified annual percentage-method brackets (sample, resembling recent years).
_FED_BRACKETS = {
    "single": [
        [0, 0.10], [11925, 0.12], [48475, 0.22], [103350, 0.24],
        [197300, 0.32], [250525, 0.35], [626350, 0.37],
    ],
    "married_joint": [
        [0, 0.10], [23850, 0.12], [96950, 0.22], [206700, 0.24],
        [394600, 0.32], [501050, 0.35], [751600, 0.37],
    ],
}
_FED_BRACKETS["married_separate"] = _FED_BRACKETS["single"]
_FED_BRACKETS["head_of_household"] = _FED_BRACKETS["single"]
_FED_STD_DEDUCTION = {
    "single": 15000, "married_joint": 30000,
    "married_separate": 15000, "head_of_household": 22500,
}
# NJ simplified single-rate sample for withholding estimation.
_NJ_BRACKETS = {"default": [[0, 0.014], [20000, 0.0175], [35000, 0.035],
                            [40000, 0.05525], [75000, 0.0637], [500000, 0.0897]]}


def _add(db, jurisdiction, tax_type, rules: list[tuple]):
    rs = TaxRuleset(
        jurisdiction=jurisdiction, tax_type=tax_type, tax_year=SAMPLE_YEAR,
        version=1, effective_date=date(SAMPLE_YEAR, 1, 1), status="draft",
        source_citation=_DISCLAIMER,
    )
    db.add(rs)
    db.flush()
    for key, num, js in rules:
        db.add(TaxRule(ruleset_id=rs.id, key=key, value_num=num,
                       value_json=json.dumps(js) if js is not None else None))
    return rs


def seed_sample_tax_rules(db: Session) -> int:
    """Seed sample rulesets once. Returns number of rulesets created (0 if present)."""
    if get_ruleset(db, "US", "ss", SAMPLE_YEAR):
        return 0
    _add(db, "US", "ss", [("rate", Decimal("0.062"), None),
                          ("wage_base", Decimal("181500"), None)])
    _add(db, "US", "medicare", [("rate", Decimal("0.0145"), None)])
    _add(db, "US", "addl_medicare", [("rate", Decimal("0.009"), None),
                                     ("threshold", Decimal("200000"), None)])
    _add(db, "US", "futa", [("rate", Decimal("0.006"), None),
                            ("wage_base", Decimal("7000"), None)])
    _add(db, "NJ", "suta", [("wage_base", Decimal("43300"), None)])
    _add(db, "US", "fed_withholding",
         [("standard_deduction", None, _FED_STD_DEDUCTION),
          ("brackets", None, _FED_BRACKETS)])
    _add(db, "NJ", "state_withholding", [("brackets", None, _NJ_BRACKETS)])
    db.commit()
    return 7


def bracket_tax(annual_taxable: Decimal, brackets: list) -> Decimal:
    """Progressive tax from [[threshold, rate], ...] sorted ascending."""
    if annual_taxable <= 0:
        return Decimal("0")
    tax = Decimal("0")
    for i, (threshold, rate) in enumerate(brackets):
        threshold = Decimal(str(threshold))
        rate = Decimal(str(rate))
        upper = Decimal(str(brackets[i + 1][0])) if i + 1 < len(brackets) else None
        if annual_taxable > threshold:
            top = min(annual_taxable, upper) if upper is not None else annual_taxable
            tax += (top - threshold) * rate
        else:
            break
    return tax
