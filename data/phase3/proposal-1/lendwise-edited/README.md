# Lendwise (fictional)

Lendwise is a small synthetic Indian NBFC-style lending platform created as a code-analysis target for Mitro. It contains no real customer data and does not connect to real providers or move money. Its deliberate weaknesses are engineering test scenarios, not conclusions that any regulation has been violated.

## Included code paths

- Loan application intake and status changes
- Synthetic KYC provider call and result handling
- Demo credit decision and loan account creation
- Co-lending partner handoff and repayment posting
- Customer support lookup
- CSV portfolio export job
- A scenario catalog of planted issues and secure decoys
- A synthetic stage-level ECL helper with a DLG invocation-adjustment gap and a no-DLG secure decoy

The default KYC provider hostname is reserved (`.invalid`). The integration has a planted TLS verification defect for static analysis; do not configure a real provider URL. All other integrations are local stubs.

## Run locally

Requires Python 3.11+. From this directory:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. The default database is a local SQLite file at `var/lendwise.db`; set `DATABASE_URL` to use PostgreSQL. On startup the service creates its tables. Use only synthetic inputs.

Run `python -m jobs.export_portfolio` to create a synthetic CSV export under `var/exports/`.

## Mitro finding policy

The cases in `compliance/scenario-catalog.yaml` are engineering test fixtures. Amend may identify candidate code locations, but must not call a case a regulatory finding unless a qualified reviewer links it to an applicable, approved obligation. The catalog also lists secure decoys so the analyzer can measure false positives.

## Routes

- `POST /api/v1/applications` — primary intake, checks the consent flag
- `POST /api/v1/applications/legacy-import` — planted consent-validation gap
- `POST /api/v1/applications/{id}/evaluate` — demo credit policy
- `GET /api/v1/applications/{id}` — application lookup
- `POST /api/v1/loans/{id}/repayments` — repayment posting
- `POST /api/v1/partners/{partner}/disbursements` — local partner handoff
- `GET /api/v1/support/customers/{id}` — planted access-control gap
- `POST /api/v1/provisioning/ecl` — synthetic stage-level DLG/ECL example for the RBI paragraph 36C demo
- `GET /health` — health check
