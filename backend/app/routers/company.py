"""Company management — supports multiple companies per user (his C-corp, her LLC)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_company
from app.core.security import encrypt_field, decrypt_field, mask_tail
from app.models.user import User, UserCompany
from app.models.company import Company
from app.services.coa import seed_chart_of_accounts
from app.services import audit
from app.schemas import CompanyIn, CompanyOut

router = APIRouter(prefix="/companies", tags=["companies"])


def _to_out(company: Company, role: str | None = None) -> CompanyOut:
    ein = decrypt_field(company.ein_encrypted) if company.ein_encrypted else None
    return CompanyOut(
        id=company.id, name=company.name, business_type=company.business_type,
        state=company.state, ein_masked=mask_tail(ein) if ein else None,
        sales_tax_default_rate=company.sales_tax_default_rate, role=role,
    )


@router.get("", response_model=list[CompanyOut])
def list_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    links = db.query(UserCompany).filter(UserCompany.user_id == user.id).all()
    out = []
    for link in links:
        c = db.get(Company, link.company_id)
        if c:
            out.append(_to_out(c, link.role))
    return out


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(body: CompanyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = Company(
        name=body.name, business_type=body.business_type, state=body.state,
        ein_encrypted=encrypt_field(body.ein), address_line1=body.address_line1,
        city=body.city, zip=body.zip, payroll_frequency=body.payroll_frequency,
        sales_tax_default_rate=body.sales_tax_default_rate,
    )
    db.add(company)
    db.flush()
    db.add(UserCompany(user_id=user.id, company_id=company.id, role="owner"))
    seed_chart_of_accounts(db, company.id)
    audit.record(db, company_id=company.id, user_id=user.id, action="create",
                 entity_type="company", entity_id=company.id, after={"name": company.name})
    db.commit()
    return _to_out(company, "owner")


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    return _to_out(company)


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: str, body: CompanyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    before = {"name": company.name, "business_type": company.business_type}
    company.name = body.name
    company.business_type = body.business_type
    company.state = body.state
    if body.ein is not None:
        company.ein_encrypted = encrypt_field(body.ein)
    company.address_line1 = body.address_line1
    company.city = body.city
    company.zip = body.zip
    company.payroll_frequency = body.payroll_frequency
    company.sales_tax_default_rate = body.sales_tax_default_rate
    audit.record(db, company_id=company.id, user_id=user.id, action="update",
                 entity_type="company", entity_id=company.id, before=before,
                 after={"name": company.name, "business_type": company.business_type})
    db.commit()
    return _to_out(company)
