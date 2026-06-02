# Build roadmap (MVP order)

Each MVP is independently useful. The senior-friendly UI, audit logging, encryption, backups, and rule-engine discipline are built in from MVP 1, not added later.

## MVP 1 — Daily bookkeeping  ← built (on `mvp1-bookkeeping`)
- [x] Core setup: auth (email/password), multi-company setup, append-only audit log
- [x] Simplified chart of accounts (preloaded for apparel/embroidery/signs, NJ)
- [x] Income entry with explain-before-post preview (cash/check/cc/ach/zelle/venmo, sales tax)
- [x] Expense entry with preview (vendor, category, deductible/CPA-review flags)
- [x] Bank CSV import (map columns, dedupe, suggest categories, "needs review")
- [x] Reports: P&L, Balance Sheet, General Ledger, Trial Balance (PDF/CSV)
- [x] CPA export package (ZIP)
- [x] Senior-friendly React frontend (big fonts, wizards, plain English)
- [~] Phase 1.5: QuickBooks import module + CSV path built; live QBO OAuth wired at deploy
- [ ] Still to add: receipt upload + OCR, optional MFA, backup/restore UI, bank reconciliation (Phase 6)

## MVP 2 — Payroll  ← built (on `mvp2-payroll`)
- [x] Employee setup (encrypted SSN/direct deposit), employer setup, per-company
- [x] Payroll run wizard (period → hours → calculate → review → approve → post)
- [x] Versioned, effective-dated tax-rule engine; sample 2026 rates seeded as DRAFT, approve-before-use
- [x] Calculation engine: gross, fed/NJ withholding (bracket method), SS/Medicare + addl Medicare, FUTA/SUTA, with YTD wage-base caps; records rule versions used
- [x] Balanced payroll journal entry on post; books stay tied out
- [x] Pay stubs (PDF), payroll register, employer-tax + tax-liability reports, 941/940 worksheet data
- [x] Senior-friendly payroll screens with prominent "sample/draft rates" warning
- [ ] Still to add: direct-deposit ACH file (intentionally out — spec defers), W-2/W-3 year-end forms

## MVP 3 — Sales tax & tax organization
- [ ] Sales tax rates/collected/payable/payments + reports
- [ ] Secure tax-document vault (by tax year, tagged, searchable)
- [ ] Small-business tax worksheets (Schedule C style, etc.)
- [ ] Personal tax organizer (document checklist + upload)
- [ ] Full CPA tax export package

## MVP 4 — Smart helpers
- [ ] AI bookkeeper (read-only Q&A; approval-gated category suggestions)
- [ ] AI tax organizer (guided questions, CPA checklist)
- [ ] Tax estimate engine (versioned rules, explanations, disclaimers)
- [ ] Missing-document detection

## MVP 5 — E-file investigation (research only)
- [ ] Gated behind tax attorney/CPA sign-off, IRS/state approval, compliance + security review (see ARCHITECTURE.md §9)
