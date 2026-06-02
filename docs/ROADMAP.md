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

## MVP 2 — Payroll
- [ ] Employee setup (encrypted SSN/direct deposit), employer setup
- [ ] Payroll run wizard (period → hours → calculate → approve → post)
- [ ] Configurable, versioned tax tables with review-before-use
- [ ] Pay stubs (PDF), payroll register, payroll-tax liability reports

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
