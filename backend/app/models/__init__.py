"""Import all models so SQLAlchemy's metadata is fully registered."""
from app.models.user import User, UserCompany
from app.models.company import (
    Company, CompanyOwner, BankAccountName, FiscalYear, CpaContact, Setting,
)
from app.models.account import Account
from app.models.ledger import JournalEntry, JournalLine
from app.models.transactions import Customer, Vendor, Income, Expense
from app.models.bank import (
    BankCsvMapping, BankImportBatch, BankTransaction, CategorizationRule,
)
from app.models.audit import AuditLog

__all__ = [
    "User", "UserCompany", "Company", "CompanyOwner", "BankAccountName",
    "FiscalYear", "CpaContact", "Setting", "Account", "JournalEntry",
    "JournalLine", "Customer", "Vendor", "Income", "Expense", "BankCsvMapping",
    "BankImportBatch", "BankTransaction", "CategorizationRule", "AuditLog",
]
