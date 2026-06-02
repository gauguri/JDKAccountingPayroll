"""Pydantic request/response models."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---- auth ----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    company_name: str
    business_type: str = "sole_prop"
    state: str = "NJ"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str | None = None


# ---- company ----
class CompanyIn(BaseModel):
    name: str
    business_type: str = "sole_prop"
    state: str = "NJ"
    ein: str | None = None
    address_line1: str | None = None
    city: str | None = None
    zip: str | None = None
    payroll_frequency: str = "biweekly"
    sales_tax_default_rate: Decimal = Decimal("0.06625")


class CompanyOut(BaseModel):
    id: str
    name: str
    business_type: str
    state: str
    ein_masked: str | None = None
    sales_tax_default_rate: Decimal
    role: str | None = None


# ---- accounts ----
class AccountIn(BaseModel):
    name: str
    type: str
    subtype: str | None = None
    code: str | None = None
    description_plain: str | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str | None = None
    name: str
    type: str
    subtype: str | None = None
    description_plain: str | None = None
    is_active: bool
    hidden: bool
    system_locked: bool


# ---- income / expense ----
class IncomeIn(BaseModel):
    date: date
    amount: Decimal
    payment_method: str
    income_account_id: str
    deposit_account_id: str | None = None
    customer_name: str | None = None
    sales_tax_collected: Decimal = Decimal("0")
    taxable: bool = True
    notes: str | None = None


class ExpenseIn(BaseModel):
    date: date
    amount: Decimal
    payment_method: str
    expense_account_id: str
    paid_from_account_id: str | None = None
    vendor_name: str | None = None
    business_purpose: str | None = None
    tax_deductible: bool = True
    reimbursable: bool = False
    cpa_review: bool = False
    notes: str | None = None


class PreviewLine(BaseModel):
    account_name: str
    debit: Decimal
    credit: Decimal


class PreviewOut(BaseModel):
    explanation: str
    lines: list[PreviewLine]


# ---- bank import ----
class BankMapIn(BaseModel):
    bank_label: str
    column_map: dict  # {"date": "...", "description": "...", "amount": "..."}


class BankRow(BaseModel):
    date: date
    description: str | None = None
    amount: Decimal
