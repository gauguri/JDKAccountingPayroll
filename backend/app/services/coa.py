"""Preloaded chart of accounts for a custom apparel / embroidery / signs business."""
from sqlalchemy.orm import Session

from app.models.account import Account, NORMAL_BALANCE

# (code, name, type, subtype, plain-English description, normal_balance override)
PRELOADED = [
    # Income
    ("4000", "Sales Income", "income", None, "Money from selling products like shirts, hats, and signs."),
    ("4010", "Service Income", "income", None, "Money from services like embroidery or design work."),
    ("4090", "Other Income", "income", None, "Any other money coming in that isn't a normal sale."),
    # Expenses
    ("5000", "Rent", "expense", None, "Rent for your shop or workspace."),
    ("5010", "Supplies", "expense", None, "General supplies used to run the business."),
    ("5020", "Blank Shirts / Hats", "expense", "cogs", "Blank shirts and hats you buy to customize."),
    ("5030", "Vinyl / Sign Materials", "expense", "cogs", "Vinyl, substrates, and other sign-making materials."),
    ("5040", "Embroidery Supplies", "expense", "cogs", "Thread, backing, and other embroidery materials."),
    ("5100", "Payroll Wages", "expense", None, "Wages paid to employees."),
    ("5110", "Payroll Taxes", "expense", None, "Employer share of payroll taxes."),
    ("5200", "Utilities", "expense", None, "Electric, gas, water for the shop."),
    ("5210", "Insurance", "expense", None, "Business insurance premiums."),
    ("5220", "Advertising", "expense", None, "Ads, signs, online promotion."),
    ("5230", "Bank Fees", "expense", None, "Fees your bank or card processor charges."),
    ("5240", "Professional Fees", "expense", None, "Accountant, lawyer, and other professional help."),
    ("5250", "Meals", "expense", None, "Business meals (often only partly deductible — CPA reviews)."),
    ("5260", "Vehicle / Fuel", "expense", None, "Gas and vehicle costs for business use."),
    ("5270", "Repairs and Maintenance", "expense", None, "Fixing equipment or the shop."),
    ("5280", "Software Subscriptions", "expense", None, "Monthly software and apps."),
    ("5290", "Telephone / Internet", "expense", None, "Phone and internet service."),
    ("5300", "Postage / Shipping", "expense", None, "Shipping and postage costs."),
    ("5900", "Miscellaneous", "expense", None, "Anything that doesn't fit another category."),
    # Assets
    ("1000", "Checking Account", "asset", "bank", "Your main business checking account."),
    ("1010", "Savings Account", "asset", "bank", "Business savings account."),
    ("1020", "Cash", "asset", "bank", "Cash on hand in the shop."),
    ("1100", "Accounts Receivable", "asset", None, "Money customers owe you but haven't paid yet."),
    ("1500", "Equipment", "asset", None, "Machines and equipment you own."),
    ("1510", "Accumulated Depreciation", "asset", "contra", "Tracks wear-and-tear value of equipment over time.", "credit"),
    # Liabilities
    ("2000", "Credit Card", "liability", None, "Business credit card balance you owe."),
    ("2100", "Payroll Taxes Payable", "liability", None, "Payroll taxes you've withheld and owe."),
    ("2110", "Sales Tax Payable", "liability", None, "Sales tax you collected and owe New Jersey."),
    ("2200", "Loans", "liability", None, "Business loans you need to pay back."),
    ("2300", "Accounts Payable", "liability", None, "Bills you owe vendors but haven't paid yet."),
    # Equity
    ("3000", "Owner Contributions", "equity", None, "Money the owners put into the business."),
    ("3010", "Owner Draws", "equity", None, "Money the owners take out for personal use."),
    ("3900", "Retained Earnings", "equity", None, "Profit kept in the business from past years."),
    ("3910", "Current Year Earnings", "equity", None, "Profit or loss so far this year."),
]


def seed_chart_of_accounts(db: Session, company_id: str) -> int:
    """Create the preloaded accounts for a company. Returns count created."""
    created = 0
    for row in PRELOADED:
        code, name, atype, subtype, desc = row[0], row[1], row[2], row[3], row[4]
        normal = row[5] if len(row) > 5 else NORMAL_BALANCE[atype]
        db.add(
            Account(
                company_id=company_id,
                code=code,
                name=name,
                type=atype,
                subtype=subtype,
                description_plain=desc,
                normal_balance=normal,
                system_locked=True,
            )
        )
        created += 1
    db.flush()
    return created


def find_account(db: Session, company_id: str, name: str) -> Account | None:
    return (
        db.query(Account)
        .filter(Account.company_id == company_id, Account.name == name)
        .first()
    )


# Simple keyword -> account-name suggestions for the "suggest" endpoint.
SUGGEST_KEYWORDS = {
    "rent": "Rent", "lease": "Rent",
    "shirt": "Blank Shirts / Hats", "hat": "Blank Shirts / Hats", "tee": "Blank Shirts / Hats",
    "vinyl": "Vinyl / Sign Materials", "sign": "Vinyl / Sign Materials", "substrate": "Vinyl / Sign Materials",
    "thread": "Embroidery Supplies", "embroider": "Embroidery Supplies",
    "electric": "Utilities", "gas bill": "Utilities", "water": "Utilities",
    "insurance": "Insurance",
    "facebook": "Advertising", "google ad": "Advertising", "ad": "Advertising",
    "bank fee": "Bank Fees", "service charge": "Bank Fees",
    "cpa": "Professional Fees", "accountant": "Professional Fees", "lawyer": "Professional Fees",
    "lunch": "Meals", "dinner": "Meals", "restaurant": "Meals",
    "fuel": "Vehicle / Fuel", "gasoline": "Vehicle / Fuel", "shell": "Vehicle / Fuel",
    "repair": "Repairs and Maintenance",
    "adobe": "Software Subscriptions", "subscription": "Software Subscriptions", "software": "Software Subscriptions",
    "verizon": "Telephone / Internet", "internet": "Telephone / Internet", "phone": "Telephone / Internet",
    "usps": "Postage / Shipping", "ups": "Postage / Shipping", "fedex": "Postage / Shipping", "shipping": "Postage / Shipping",
}


def suggest_account_name(description: str) -> str | None:
    d = (description or "").lower()
    for kw, name in SUGGEST_KEYWORDS.items():
        if kw in d:
            return name
    return None
