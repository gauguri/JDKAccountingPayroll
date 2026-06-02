# Build roadmap (MVP order)

Each MVP is independently useful. The senior-friendly UI, audit logging, encryption, backups, and rule-engine discipline are built in from MVP 1, not added later.

## MVP 1 — Daily bookkeeping  ← build next
- [ ] Core setup: auth (email/password + optional MFA), company setup wizard, fiscal year, settings
- [ ] Backup/restore + append-only audit log
- [ ] Simplified chart of accounts (preloaded for apparel/embroidery/signs)
- [ ] Income entry wizard (cash/check/cc/ach/zelle/venmo, sales tax, taxable flag)
- [ ] Expense entry wizard (vendor, category, receipt upload, OCR suggestion, deductible/CPA-review flags)
- [ ] Bank CSV import (map columns, dedupe, match, "needs review")
- [ ] Reports: P&L, Balance Sheet, General Ledger, Trial Balance (PDF/CSV)
- [ ] CPA export package (ZIP)
- [ ] Phase 1.5: QuickBooks (QBO/QBD/CSV/IIF) import + migration report

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
