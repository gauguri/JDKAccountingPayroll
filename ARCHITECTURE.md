# JDK Books — System Architecture (Phase 0)

**Product:** A very simple QuickBooks alternative for a tiny 2-person business.
**Users:** A husband and wife, age 70, who run a custom apparel/embroidery/t-shirt shop and a custom signs shop. They are not accountants.
**Promise:** Bookkeeping, payroll, and tax *organization* for mom-and-pop businesses that hate QuickBooks — cheaper and simpler.

**Explicitly NOT building:** CRM, ERP, inventory, order management, production management, or large-enterprise accounting. No automatic tax/payroll e-filing in early versions — we *prepare* reports, worksheets, and a CPA export package.

---

## 0. Design principles (these constrain every later decision)

1. **Senior-friendly first.** Large fonts (16px base, 18–20px body), high contrast, few buttons per screen, plain English, no jargon unless unavoidable, and a glossary tooltip when it is.
2. **Wizard, not dashboard.** Every multi-step task is a guided flow with one decision per screen and a clear "what happens next" summary.
3. **Explain before you post.** No transaction touches the books until the user sees a plain-English preview ("This will record $200 of income and $15 of sales tax you owe New Jersey").
4. **AI never silently changes the books.** Every AI action is a *suggestion* that the user approves. Uncertain items are flagged "Needs Review," never auto-posted.
5. **Honest positioning.** The software organizes; the CPA files. We never claim to be IRS-approved filing software, to guarantee compliance, or to replace a CPA.
6. **Tax rules are data, not code.** No tax rate, bracket, or threshold is hardcoded in business logic. All of it lives in versioned, effective-dated rule tables that a human reviews before use.

---

## 1. Architecture diagram (text)

```
┌──────────────────────────────────────────────────────────────────────┐
│                         USER'S BROWSER                                 │
│   React + TypeScript + Tailwind  (large-font, wizard-style SPA)        │
│   - Home: "What do you want to do today?"                              │
│   - Wizards: income, expense, bank import, reconcile, payroll, taxes   │
│   - Reports & CPA export                                               │
└───────────────┬────────────────────────────────────────────────────────┘
                │ HTTPS (JSON REST), JWT in HttpOnly cookie
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    BACKEND — Python FastAPI                            │
│                                                                        │
│  API layer (routers)        Service layer (business rules)             │
│  ┌────────────────┐        ┌──────────────────────────────────────┐  │
│  │ auth           │        │ AccountingService (double-entry)      │  │
│  │ company        │        │ PayrollService                        │  │
│  │ accounts       │        │ SalesTaxService                       │  │
│  │ income/expense │───────▶│ ReconciliationService                 │  │
│  │ bank-import    │        │ ReportService                         │  │
│  │ payroll        │        │ TaxEstimateService (rule-engine)      │  │
│  │ sales-tax      │        │ ImportService (QBO/QBD/CSV/IIF)       │  │
│  │ reports        │        │ CpaExportService                      │  │
│  │ documents      │        │ AuditService (writes to every change) │  │
│  │ tax-prep       │        └──────────────┬───────────────────────┘  │
│  │ ai-assistant   │                       │                           │
│  └───────┬────────┘                       │                           │
│          │                                 │                           │
│   ┌──────▼─────────┐   ┌──────────────────▼──────┐  ┌──────────────┐ │
│   │ Rule Engine    │   │ Repository / ORM        │  │ Crypto       │ │
│   │ (tax tables,   │   │ (SQLAlchemy)            │  │ (field-level │ │
│   │  versioned,    │   └──────────┬──────────────┘  │  AES-GCM for │ │
│   │  eff-dated)    │              │                  │  SSN, DD)    │ │
│   └────────────────┘              │                  └──────────────┘ │
└───────────────────────────────────┼────────────────────────────────────┘
            │                        │                       │
            ▼                        ▼                       ▼
   ┌─────────────────┐   ┌─────────────────────┐   ┌────────────────────┐
   │ PostgreSQL      │   │ Object storage      │   │ External (optional, │
   │ - books/ledger  │   │ (receipts, docs,    │   │  later phases)      │
   │ - payroll       │   │  CPA ZIPs)          │   │ - LLM API (AI asst) │
   │ - tax rules     │   │ local fs / S3-compat│   │ - QBO OAuth         │
   │ - audit log     │   │ encrypted at rest   │   │ - Bank aggregator   │
   └─────────────────┘   └─────────────────────┘   │ - IRS/state e-file  │
                                                     └────────────────────┘

   Deployment: Docker Compose — containers: web (nginx+static), api (FastAPI/uvicorn),
   db (Postgres), worker (background jobs: OCR, imports, exports), object-store.
```

Key flows:

- **Posting a transaction** always goes API → Service → (preview returned to user) → user confirms → Service writes journal entries inside one DB transaction → AuditService records who/what/when/before/after.
- **Tax math** never lives in services directly; services *ask the Rule Engine* "what is the SUTA rate for NJ effective 2026-01-01?" and the engine returns the value plus the rule version used, which is stored on the calculation for traceability.

---

## 2. Database schema (PostgreSQL)

Conventions: every table has `id` (UUID), `company_id` (tenant scope, except global tax-rule tables), `created_at`, `updated_at`, `created_by`, `updated_by`. Soft-delete via `is_active`/`hidden` where deletion must be prevented. Money stored as `NUMERIC(14,2)`; rates as `NUMERIC(9,6)`.

### Identity & company

```
users(id, email UNIQUE, password_hash, role, mfa_secret NULL, is_active,
      last_login_at, failed_login_count, locked_until)
  role ∈ {owner, admin, bookkeeper, payroll, cpa_readonly}

company(id, name, ein_encrypted, address_line1, address_line2, city,
        state, zip, business_type, payroll_frequency, tax_year,
        sales_tax_default_rate, created_at)
  business_type ∈ {sole_prop, smllc, partnership, s_corp, c_corp}

company_owner(id, company_id, name, ownership_pct, is_signer)
bank_account_name(id, company_id, label, last4 NULL, gl_account_id)  -- nicknames only
cpa_contact(id, company_id, name, firm, email, phone, notes)
fiscal_year(id, company_id, year, start_date, end_date, status)
  status ∈ {open, closed}
settings(id, company_id, key, value_json)  -- misc app settings
user_company(user_id, company_id, role)  -- supports husband+wife+CPA on one company
```

### Chart of accounts & ledger (double-entry core)

```
account(id, company_id, code, name, type, subtype, description_plain,
        normal_balance, is_active, hidden, system_locked)
  type ∈ {income, expense, asset, liability, equity}
  normal_balance ∈ {debit, credit}
  system_locked = true for preloaded accounts that must not be deleted

journal_entry(id, company_id, entry_date, memo, source_type, source_id,
              posted, reversed_by NULL, created_by)
  source_type ∈ {income, expense, payroll, bank, sales_tax, reconcile,
                 opening_balance, import, manual}

journal_line(id, journal_entry_id, account_id, debit, credit, memo)
  CONSTRAINT: per entry, SUM(debit) = SUM(credit)
```

All money movement (income, expense, payroll, sales tax) produces a `journal_entry` + balanced `journal_line`s. Reports read from the ledger, so P&L / Balance Sheet always tie out.

### Income & expense (the friendly front-ends to journal entries)

```
customer(id, company_id, name, email NULL, notes)      -- optional, no CRM
vendor(id, company_id, name, is_1099, tin_encrypted NULL, address, notes)

income(id, company_id, date, customer_id NULL, amount, payment_method,
       account_id, sales_tax_collected, taxable, deposit_group_id NULL,
       notes, attachment_id NULL, recurring_id NULL, journal_entry_id)
  payment_method ∈ {cash, check, credit_card, ach, zelle, venmo}

expense(id, company_id, date, vendor_id, amount, payment_method, account_id,
        business_purpose, reimbursable, tax_deductible, cpa_review,
        attachment_id NULL, recurring_id NULL, journal_entry_id)

recurring_template(id, company_id, kind, cadence, next_run, payload_json)
  kind ∈ {income, expense}

mileage(id, company_id, date, miles, purpose, vehicle, business_pct, rate_id)
home_office(id, company_id, tax_year, total_sqft, office_sqft, method, notes)
```

### Bank import & reconciliation

```
bank_import_batch(id, company_id, bank_account_id, filename, mapping_id,
                  row_count, status, created_at)
bank_csv_mapping(id, company_id, bank_label, column_map_json)  -- remembered per bank
bank_transaction(id, company_id, bank_account_id, date, description, amount,
                 direction, status, matched_type NULL, matched_id NULL,
                 split_parent_id NULL, attachment_id NULL, batch_id)
  direction ∈ {debit, credit};  status ∈ {unmatched, matched, needs_review, added, ignored}
categorization_rule(id, company_id, match_text, account_id, priority)

reconciliation(id, company_id, bank_account_id, start_date, end_date,
               beginning_balance, ending_balance, status, difference, created_by)
reconciliation_item(id, reconciliation_id, bank_transaction_id, cleared)
```

### Payroll

```
employee(id, company_id, first_name, last_name, address, ssn_encrypted,
         email, pay_type, pay_rate, filing_status, fed_withholding_json,
         state_withholding_json, dd_info_encrypted NULL, start_date, is_active)
  pay_type ∈ {hourly, salary}

employer_payroll_setup(id, company_id, state_employer_id_encrypted,
         payroll_schedule, suta_rate, local_tax_json)

payroll_run(id, company_id, pay_period_start, pay_period_end, pay_date,
            status, tax_table_version_id, journal_entry_id, created_by)
  status ∈ {draft, calculated, approved, posted}

payroll_item(id, payroll_run_id, employee_id, hours, gross_pay,
             fed_wh, state_wh, ss_employee, medicare_employee,
             ss_employer, medicare_employer, futa, suta, net_pay,
             calc_explanation_json)   -- stores which rule versions were used

pay_stub(id, payroll_item_id, pdf_attachment_id, issued_at)
```

### Sales tax

```
sales_tax_rate(id, company_id, jurisdiction, level, rate, effective_date, end_date)
  level ∈ {state, county, city}
sales_tax_period(id, company_id, period_start, period_end, collected,
                 taxable_sales, exempt_sales, payable, status)
sales_tax_payment(id, company_id, period_id, date, amount, journal_entry_id)
exemption_certificate(id, company_id, customer_id, attachment_id, expires_on)
```

### Tax rule engine (global, versioned — the heart of compliance)

```
tax_ruleset(id, jurisdiction, tax_type, tax_year, version, effective_date,
            end_date, status, reviewed_by, reviewed_at, source_citation)
  jurisdiction ∈ {US, NJ, NY, PA, CT, ...}
  tax_type ∈ {fed_income, state_income, se_tax, ss, medicare, futa, suta,
              sales_tax, withholding}
  status ∈ {draft, under_review, approved, retired}   -- only 'approved' is usable

tax_rule(id, ruleset_id, key, value_json, notes)
  -- e.g. brackets, rates, wage bases, standard deduction amounts
```

Calculations reference `tax_ruleset.version`, and that version id is persisted on `payroll_item` / tax estimates so any number can be reproduced and audited later.

### Documents & audit

```
attachment(id, company_id, tax_year NULL, doc_type, original_name,
           storage_key, mime, size, sha256, encrypted, uploaded_by)
  doc_type ∈ {receipt, bank_statement, w2, 1099_nec, 1099_misc, 1099_k,
              1099_int, 1099_div, 1099_b, 1099_r, ssa_1099, k1,
              prior_return, payroll_report, sales_tax_filing, cpa_corr, other}

tax_profile(id, company_id, tax_year, taxpayer_name, spouse_name,
            filing_status, address, dependents_json, ...encrypted SSNs/DOB)

audit_log(id, company_id, user_id, action, entity_type, entity_id,
          before_json, after_json, ip, user_agent, created_at)  -- append-only
ai_suggestion(id, company_id, context, suggestion_json, status, decided_by,
              decided_at)  -- status ∈ {pending, approved, rejected}
```

---

## 3. API design (FastAPI, REST)

All routes are under `/api`, return JSON, require auth except `/auth/login` and `/auth/register`. Standard error envelope: `{error: {code, message, fields?}}`. Pagination via `?page=&size=`. Every write endpoint that posts to the books has a paired **preview** endpoint that returns the plain-English explanation and the proposed journal lines *without* saving.

```
Auth & users
  POST   /auth/register            create first owner + company
  POST   /auth/login               -> sets HttpOnly JWT cookie
  POST   /auth/logout
  POST   /auth/mfa/enable | verify
  GET    /me

Company
  GET/PUT  /company
  CRUD     /company/owners
  CRUD     /company/bank-accounts
  CRUD     /company/cpa-contacts
  CRUD     /fiscal-years
  GET/PUT  /settings

Accounts
  GET    /accounts                 (filter by type, include hidden?)
  POST   /accounts
  PUT    /accounts/{id}
  POST   /accounts/{id}/hide
  GET    /accounts/suggest?desc=   -> account suggestion for a description

Income / Expense
  GET/POST/PUT/DELETE  /income      (DELETE blocked if reconciled)
  POST   /income/preview            -> {explanation, journal_lines}
  GET/POST/PUT/DELETE  /expenses
  POST   /expenses/preview
  POST   /expenses/{id}/ocr         -> OCR suggestion (needs approval)
  CRUD   /recurring
  CRUD   /mileage
  GET/PUT /home-office/{tax_year}

Bank import / reconcile
  POST   /bank-import/upload        (multipart CSV)
  POST   /bank-import/map           save/apply column mapping
  GET    /bank-import/{batch}/preview
  POST   /bank-import/{batch}/commit
  POST   /bank-transactions/{id}/match | split | reclassify
  CRUD   /reconciliations
  POST   /reconciliations/{id}/toggle-item

Payroll
  CRUD   /employees                 (SSN/DD encrypted; payroll role required)
  GET/PUT /payroll/employer-setup
  POST   /payroll/runs              create draft
  POST   /payroll/runs/{id}/calculate   -> per-employee breakdown + explanations
  POST   /payroll/runs/{id}/approve
  POST   /payroll/runs/{id}/post        -> writes journal entry
  GET    /payroll/runs/{id}/stubs       -> PDF links
  GET    /payroll/reports/{type}

Sales tax
  CRUD   /sales-tax/rates
  GET    /sales-tax/periods
  POST   /sales-tax/payments
  CRUD   /exemption-certificates

Reports & CPA export
  GET    /reports/{type}?from=&to=&format=pdf|csv|json
         type ∈ {pnl, balance_sheet, cash_flow, general_ledger, trial_balance,
                 owner_draws, payroll_summary, sales_tax_summary,
                 deductible_expenses, mileage, home_office, tax_summary}
  POST   /cpa-export                -> builds ZIP, returns download token
  GET    /cpa-export/{id}/download

Tax prep & estimates
  GET/PUT /tax-prep/personal/{tax_year}
  GET/PUT /tax-prep/business/{tax_year}
  GET    /tax-prep/missing-documents/{tax_year}
  GET    /tax-prep/worksheets/{form}        (1040org, sch_c, sch_se, 941, 940, w2, 1099_nec...)
  POST   /tax-estimate/run                  -> estimate + rule versions + disclaimer

Tax rules (admin/CPA review)
  GET    /tax-rules?jurisdiction=&type=&year=
  POST   /tax-rules/import          upload new ruleset (status=draft)
  POST   /tax-rules/{id}/approve    (admin/CPA only) draft -> approved

Documents
  POST   /documents/upload
  GET    /documents?tax_year=&type=
  GET    /documents/{id}            (logs an audit view)
  POST   /documents/export-zip

AI assistant
  POST   /ai/ask                    plain-English Q&A over the books (read-only)
  POST   /ai/suggest-categories     -> ai_suggestion rows (pending)
  POST   /ai/suggestions/{id}/approve | reject

Import / migration (Phase 1.5)
  POST   /import/qbo/connect (OAuth) | /import/qbd | /import/csv | /import/iif
  GET    /import/{job}/preview
  POST   /import/{job}/commit
  POST   /import/{job}/rollback
  GET    /import/{job}/report
```

---

## 4. Frontend page map

```
/                       Home — "What do you want to do today?" (6 big tiles)
/login  /setup          Login; first-run company setup wizard

Money in/out
  /income/new           Income wizard (date → amount → category → tax → review)
  /income               Income list + filters
  /expenses/new         Expense wizard (+ receipt upload, OCR suggestion)
  /expenses             Expense list
  /recurring            Recurring items

Bank
  /bank/import          Upload → map columns → preview → match → commit (wizard)
  /bank/reconcile       Reconcile wizard (statement balances → check off → done)

Payroll
  /payroll/employees    Employee list (sensitive fields masked)
  /payroll/run          Run payroll wizard (period → hours → review → approve → stubs)
  /payroll/reports      Payroll & payroll-tax reports

Sales tax
  /sales-tax            Rates, collected, payable, payments

Reports
  /reports              Report picker; each opens with plain-English explanation,
                        date range, and "Export PDF / CSV / Send to CPA" buttons

Taxes
  /taxes/personal       Personal tax organizer (document checklist + upload)
  /taxes/business       Business tax worksheets (Schedule C style, etc.)
  /taxes/estimate       Tax estimate dashboard (with CPA-review disclaimer)
  /cpa-export           One-click CPA package builder

Documents
  /documents            Vault by tax year, tagged, searchable

Assistant
  /assistant            AI bookkeeper/tax chat (suggestions need approval)

Settings
  /settings/company  /settings/users  /settings/tax-rules  /settings/backup
```

Shared UI conventions: a persistent "Need help?" button, breadcrumbs in every wizard ("Step 2 of 4"), a confirmation screen before any post, and a glossary tooltip on every accounting term.

---

## 5. Security design

- **Auth:** email/password with Argon2id hashing; JWT in an HttpOnly, Secure, SameSite=Strict cookie; short access token + refresh; account lockout after repeated failures. Optional TOTP MFA, *required* for the payroll and tax-document areas.
- **Authorization:** role-based (`owner`, `admin`, `bookkeeper`, `payroll`, `cpa_readonly`). Payroll SSNs/direct-deposit and tax SSNs are visible only to `payroll`/`owner`. CPA gets read-only.
- **Field-level encryption:** SSNs, EIN, TINs, and direct-deposit details encrypted with AES-256-GCM using a key from a KMS/secret store (never in the DB or code). Decrypted only in-memory when authorized; masked (•••-••-1234) everywhere else.
- **Encryption in transit & at rest:** TLS everywhere; Postgres and object storage encrypted at rest; document blobs encrypted before write.
- **Tenant isolation:** every query scoped by `company_id`; enforced in the repository layer, not left to callers.
- **Input safety:** Pydantic validation on all inputs; parameterized queries (no string SQL); CSRF protection on cookie-auth routes; rate limiting on auth and AI endpoints; antivirus + type/size checks on uploads.
- **Secrets & dependencies:** secrets via environment/secret manager; dependency scanning and pinned versions in Docker images.
- **AI boundary:** the AI assistant has read-only DB access and can only *create suggestions*; it can never write a journal entry. Prompts are scoped to the user's own company data.

---

## 6. Backup & restore strategy

- **Database:** nightly automated `pg_dump` (logical) + continuous WAL archiving for point-in-time recovery. Backups encrypted and stored off the app host (separate volume/bucket). Retention: 30 daily, 12 monthly, 7 yearly (tax records are long-lived).
- **Documents/object storage:** versioned bucket with the same retention; checksums (`sha256`) verified on restore.
- **App-level export:** a user-facing "Download a full backup" that produces an encrypted ZIP of their ledger (CSV/JSON) + documents, so the owners always have their own copy independent of us.
- **Restore drills:** documented runbook; a monthly automated restore-to-scratch test that verifies the trial balance ties out after restore.
- **Migrations:** schema changes via versioned migration tool (Alembic); always backward-tested against a restored copy before production.

---

## 7. Audit trail design

- **Append-only `audit_log`** captures user, action, entity type/id, before/after JSON snapshots, IP, and user-agent for every create/update/delete and for sensitive *reads* (viewing/downloading SSNs or tax documents, generating a CPA export).
- **Immutability of books:** posted journal entries are never edited or hard-deleted — corrections create a *reversing entry* plus a new entry, both linked, so history is preserved (matches how accountants expect books to behave).
- **Payroll changes** are individually audited (rate changes, SSN edits) because they're legally sensitive.
- **Tax rule provenance:** every calculation stores the `tax_ruleset.version` used, so any number can be traced to an approved, effective-dated rule with a source citation.
- **AI accountability:** every AI suggestion and the user's approve/reject decision is recorded.
- **Access:** audit log is viewable by `owner`/`admin`, read-only, exportable for the CPA, and protected from modification at the application layer.

---

## 8. Tax compliance risk areas (and how we mitigate)

| Risk | Mitigation |
|---|---|
| Hardcoded or stale tax rates | Rule engine only; versioned, effective-dated, `approved`-status-gated tables; annual review workflow. |
| Appearing to give tax advice / guarantee deductions | Persistent disclaimers; "estimate only — review with your CPA"; AI cannot assert final advice or guarantee deductions. |
| Payroll tax miscalculation | Configurable tax tables with human review before use; every calc shows its breakdown and rule version; outputs are CPA-reviewable worksheets, not filings. |
| Unauthorized e-filing / implying IRS approval | No e-filing in early phases; we generate worksheets/packages only; positioning copy avoids "filing software" claims. |
| Sensitive data exposure (SSN/DD/EIN) | Field-level encryption, masking, role gating, MFA on payroll/tax areas, audited access. |
| Sales tax nexus / multi-jurisdiction errors | State/county/city rate tables with effective dates; exempt-sale flags and certificate storage; reports clearly labeled "for CPA review." |
| Misclassified contractors / 1099 thresholds | 1099 vendor flag + payment tracking + a "CPA review" exceptions report rather than automated determinations. |
| Record retention / restore failure | Long retention, point-in-time recovery, monthly restore drills, user-downloadable backups. |
| Co-mingling personal/business | Owner draw/contribution tracking and separate bank-account nicknames; CPA-review flags on ambiguous items. |

Recurring theme: **prepare and organize, flag uncertainty, defer the legal determination to the CPA.**

## 9. Future e-file integration strategy (research-only, later phase)

E-filing is a distinct, advanced phase gated behind professional and legal review — explicitly **not** in early versions. The path:

1. **Research & authorization:** IRS Modernized e-File (MeF) requirements, becoming an authorized e-file provider, and passing the IRS Assurance Testing System (ATS); equivalent state requirements.
2. **Schema & validation:** generate e-file XML, validate against published schemas before any transmission.
3. **Controlled testing:** test submissions in ATS/state test environments; never against production with real returns until certified.
4. **Acknowledgment & rejection handling:** track acks, surface rejections in a plain-English correction workflow, support amended returns only if approved.
5. **Submission history & security:** immutable submission records, heightened security and audit, professional-liability review.
6. **Gates before any of this ships:** tax attorney/CPA sign-off, IRS/state approval, compliance testing, security review.

Until all gates are cleared, the product stops at the CPA export package — the CPA files.

## 10. Development roadmap

The build order follows the MVP plan; each MVP is independently useful and shippable.

**MVP 1 — Daily bookkeeping (the thing they use every day):** Core setup (auth, company, fiscal year, settings, backup, audit), simplified chart of accounts, income entry, expense entry, bank CSV import, basic financial reports (P&L, Balance Sheet, GL, Trial Balance), CPA export. *Plus Phase 1.5 QuickBooks/CSV import so they can leave QuickBooks.*

**MVP 2 — Payroll:** Employee/employer setup with encrypted SSN/DD, payroll run wizard, configurable tax tables with review, pay stubs (PDF), payroll register, payroll-tax liability reports (no auto-filing).

**MVP 3 — Sales tax & tax organization:** Sales tax tracking and reports, secure tax-document vault, small-business tax worksheets (Schedule C style etc.), personal tax organizer, and the full CPA tax export package.

**MVP 4 — Smart helpers:** AI bookkeeper (read-only Q&A + approval-gated category suggestions), AI tax organizer (guided questions, CPA checklist), tax estimate engine (versioned rules, explanations, disclaimers), missing-document detection.

**MVP 5 — E-file investigation:** research and prototype only, after the compliance/legal gates in section 9.

**Cross-cutting throughout:** the senior-friendly UI, audit logging, encryption, backups, and the rule-engine discipline are not a phase — they are built in from MVP 1.

---

*This document is Phase 0. It defines what we build and the guardrails (rules-as-data, explain-before-post, AI-suggests-only, organize-don't-file) that every later phase must respect.*
