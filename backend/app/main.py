"""JDK Books API entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import init_db, SessionLocal
from app.routers import (
    auth, company, accounts, income, expenses, bank, reports, cpa_export, imports,
    payroll, payroll_reports, tax_rules,
)
from app.services.tax_rules import seed_sample_tax_rules

app = FastAPI(title="JDK Books API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()
    # Seed sample (DRAFT) tax tables once so payroll can be demoed; they must be
    # reviewed/approved before use. No-op if already present.
    db = SessionLocal()
    try:
        seed_sample_tax_rules(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "JDK Books"}


for r in (auth, company, accounts, income, expenses, bank, reports, cpa_export, imports,
          payroll, payroll_reports, tax_rules):
    app.include_router(r.router, prefix="/api")
