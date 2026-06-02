"""Tax-rule administration: review and approve rulesets before payroll uses them.

Tax rules are global (shared across companies). Only an owner/admin should
approve a draft ruleset. Approval is what lets a rate move from 'sample/draft'
to usable in a real payroll.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.tax_rules import TaxRuleset
from app.services import audit

router = APIRouter(prefix="/tax-rules", tags=["tax-rules"])


@router.get("")
def list_rulesets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(TaxRuleset).order_by(
        TaxRuleset.jurisdiction, TaxRuleset.tax_type, TaxRuleset.version).all()
    out = []
    for rs in rows:
        out.append({
            "id": rs.id, "jurisdiction": rs.jurisdiction, "tax_type": rs.tax_type,
            "tax_year": rs.tax_year, "version": rs.version, "status": rs.status,
            "effective_date": str(rs.effective_date), "source": rs.source_citation,
            "rules": [{"key": r.key, "value_num": str(r.value_num) if r.value_num is not None
                       else None, "value_json": r.value_json} for r in rs.rules],
        })
    return out


@router.post("/{ruleset_id}/approve")
def approve(ruleset_id: str, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    rs = db.get(TaxRuleset, ruleset_id)
    if not rs:
        raise HTTPException(404, "Ruleset not found")
    rs.status = "approved"
    rs.reviewed_by = user.id
    audit.record(db, company_id=None, user_id=user.id, action="approve",
                 entity_type="tax_ruleset", entity_id=rs.id,
                 after={"status": "approved",
                        "ruleset": f"{rs.jurisdiction}/{rs.tax_type}/{rs.tax_year}v{rs.version}"})
    db.commit()
    return {"ok": True, "status": rs.status}
