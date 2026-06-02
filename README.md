# JDK Books

A very simple bookkeeping, payroll, and tax-organization tool for a tiny 2-person business — a friendlier, cheaper alternative to QuickBooks. It records income and expenses, runs payroll and prints pay stubs, tracks sales tax, explains your profit in plain English, and packages everything up for your CPA.

It does **not** try to be a giant accounting platform: no CRM, ERP, inventory, or order management — and it does **not** file taxes for you. It organizes everything so your CPA can file faster and cheaper.

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for the full Phase 0 design (database, API, security, compliance, roadmap).

## Stack

- **Frontend:** React + TypeScript + Tailwind (large-font, wizard-style)
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL
- **Auth:** email/password (optional MFA on payroll & tax areas)
- **Deployment:** Docker Compose

## Project layout

```
backend/
  app/
    routers/      API endpoints (auth, company, accounts, income, ...)
    services/     business rules (double-entry posting, payroll, reports, ...)
    models/       SQLAlchemy ORM models
    schemas/      Pydantic request/response models
    core/         config, security, db session, encryption
    rule_engine/  versioned, effective-dated tax-rule lookups
  tests/          unit + integration tests
frontend/
  src/
    pages/        top-level screens (Home, Income, Reports, ...)
    wizards/      step-by-step flows (income, payroll, reconcile, ...)
    components/   shared UI (big buttons, plain-English explainers)
    lib/          API client, formatting, glossary
docs/             additional design notes
ops/              docker, deploy, backup runbooks
```

## Getting started (once code lands in MVP 1)

```bash
cp .env.example .env          # fill in secrets
docker compose up --build     # starts db, api, web, worker
# web:  http://localhost:3000
# api:  http://localhost:8000/docs
```

## Guardrails (non-negotiable)

1. Senior-friendly UI: large fonts, few buttons, plain English, wizards.
2. Explain before you post — nothing hits the books without a preview.
3. AI suggests, never writes — every suggestion needs user approval.
4. Tax rules are versioned data, never hardcoded.
5. We organize; the CPA files. No "IRS-approved filing" claims.

## Status

Phase 0 (architecture) complete. Next: MVP 1 — core setup, chart of accounts, income/expense entry, bank CSV import, basic reports, CPA export, plus QuickBooks import.
