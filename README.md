# Mitro — Regulatory-to-Engineering Review for NBFCs
#Cybersecurity Track

**A review workspace for Indian NBFC compliance and technology teams**

| Project links | |
| --- | --- |
| **Live demo** | [mitro-r85m.onrender.com](https://mitro-r85m.onrender.com) |
| **Video walkthrough** | [Watch the Mitro demo](https://youtu.be/1eMhHhTPQFU) |

Mitro helps an NBFC team follow a review trail from a regulatory document to the software areas that may need attention. It organizes RBI and MeitY source text, clause review, proposed engineering obligations, candidate code locations, and a small set of reviewable code-change examples in one place.

Mitro is a prototype for review and demonstration. It does not decide whether a regulation applies to an NBFC, determine that an NBFC is compliant or non-compliant, or replace legal and compliance review. The included Lendwise lending platform is fictional and contains synthetic scenarios only.

## Contents

- [What Mitro does](#what-mitro-does)
- [Features](#features)
- [System architecture](#system-architecture)
- [Technology stack](#technology-stack)
- [Quick start](#quick-start)
- [Optional AI configuration](#optional-ai-configuration)
- [Typical review workflow](#typical-review-workflow)
- [API overview](#api-overview)
- [Project structure](#project-structure)
- [Data, privacy, and safety boundaries](#data-privacy-and-safety-boundaries)
- [Known limitations](#known-limitations)
- [Development and verification](#development-and-verification)

## What Mitro does

For an NBFC, a regulatory update can affect policies, customer journeys, operational controls, and software. Mitro gives compliance and technology reviewers a shared way to examine that possible connection:

1. **Read the source:** upload or review a regulatory document, inspect extracted clauses, and compare document versions.
2. **Review the requirement:** draft an engineering obligation linked to a clause, then leave applicability and approval to a human reviewer.
3. **Explore possible software impact:** scan a local codebase and inspect candidate code locations that may relate to the reviewed obligation.
4. **Evaluate a limited change example:** preview a supported Lendwise demo patch, build it in a separate copy, and run the associated regression checks.

Mitro surfaces source citations, exact clause text, file paths, and review status to help reviewers understand how a suggestion was formed. Code matches are candidate locations for investigation, not confirmed control gaps or regulatory findings.

### Who it is for

- **NBFC compliance and regulatory affairs:** organize source documents, examine clause changes, and review proposed engineering obligations.
- **NBFC technology and product teams:** investigate which code areas may relate to a reviewed requirement and discuss potential implementation work.
- **Risk and assurance reviewers:** follow the available source, obligation, scan, patch, and test evidence during a demo or internal review.

These are intended users of the prototype, not separate authenticated user roles; the local demo has no sign-in or access-control system.

### NBFC examples in the demo

The fictional Lendwise application includes synthetic lending scenarios. Mitro currently demonstrates two scoped code-change cases: consent validation in a legacy digital-lending path, and a DLG cover reduction after invocation. These examples illustrate a review workflow; they do not establish that any real NBFC has an issue or that a proposed interpretation is legally applicable.

## Features

- **Regulatory source catalog:** supplied RBI and MeitY document copies are cataloged with identifiers, dates, and provenance metadata.
- **Document ingestion:** accept PDF, text, Markdown, XML, and HTML uploads; fetch a single explicitly supplied HTTPS source URL from permitted official domains.
- **On-demand source checks:** check catalogued official URLs when requested, retain changed copies as new versions, and calculate SHA-256 hashes. This is not continuous monitoring.
- **Clause extraction and review:** extract text, segment it into clause candidates, preserve citations and source links, and flag cases that may need OCR or manual correction.
- **Version comparison:** compare versions of the same regulatory document and inspect text redlines and clause-level changes.
- **Obligation drafting and approval:** create rule-based candidates or optional model-assisted drafts. Drafts remain proposals until a human reviewer approves them.
- **Sarvam AI support:** optionally use Sarvam for Phase 1 obligation drafting from selected clause text. Sarvam is not used for repository scanning or patch generation.
- **Repository registration and scanning:** register an allowed local repository, inventory supported code, and surface candidate code locations with paths, snippets, and obligation context.
- **Regulatory change impact:** compare two document versions, find linked obligations, and map approved obligations to candidate code locations for re-review.
- **Scoped code-change examples:** preview changes for exactly two bundled Lendwise scenarios: the DLG cover reduction after invocation example and consent validation in a legacy digital-lending path.
- **Safe Patch Guard:** enforce scenario-specific file allowlists, protected paths, secret-like content checks, and patch size limits before creating a separate edited copy.
- **Regression evidence:** run generated checks in the separate copy and retain the outcome as evidence about tested behavior.
- **Dependency update impact:** inspect local dependency manifests and Python imports for a manually supplied version proposal. It does not install packages or check live vulnerability databases.
- **Audit history:** record key workflow actions such as ingestion, approval, scans, patch building, and impact analysis.
- **Local web workspace:** a landing page and workbench provide access to document review, obligations, scanning, code-change demonstrations, impact analysis, and audit history.

## System architecture

```mermaid
flowchart TB
    Reviewer[Reviewer or developer] --> Browser[Mitro web UI<br/>HTML, CSS, JavaScript]
    Browser -->|HTTP requests| API[FastAPI application]
    API --> P1
    API --> P2
    API --> P3
    API --> P4

    subgraph Workflows[Mitro workflows]
        direction LR
        P1["1. Regulatory intelligence<br/>Ingest · extract · compare · review"]
        P2["2. Code impact analysis<br/>Scan · map candidate locations"]
        P3["3. Code change demo<br/>Propose · guard · test separate copy"]
        P4["Change impact<br/>Regulatory versions · dependencies"]
    end

    subgraph Inputs[Sources and targets]
        direction LR
        Corpus[Local source corpus<br/>and uploaded documents]
        Official[Allow-listed official URLs<br/>checked on request]
        Repository[Allowed local repository<br/>Lendwise demo by default]
    end

    subgraph Storage[Local project data]
        direction LR
        Database[(SQLAlchemy database<br/>SQLite by default · PostgreSQL optional)]
        Copies[Separate demo copies<br/>tests · evidence · ZIP downloads]
        Audit[Workflow audit events]
    end

    subgraph Drafting[Optional obligation drafting providers]
        direction LR
        Sarvam[Sarvam API<br/>selected clause text only]
        Ollama[Ollama<br/>local model]
    end

    P1 -->|read / ingest| Corpus
    P1 -->|manual source check| Official
    P1 -->|documents, clauses, obligations| Database
    P1 -.->|optional draft request| Sarvam
    P1 -.->|optional local draft request| Ollama
    Sarvam -.->|draft for human review| P1
    Ollama -.->|draft for human review| P1

    P2 -->|read-only scan| Repository
    P2 -->|candidate locations| Database
    P3 -->|read source copy| Repository
    P3 -->|guarded build and regression checks| Copies
    P3 -->|proposal and evidence| Database
    P4 -->|compare versions / map candidates| Database
    P4 -->|inspect candidate code| Repository
    API -->|record workflow actions| Audit
    Audit --> Database

    Database -.->|review data and results| API
    Copies -.->|downloadable artifacts| API
```

### Data flow

1. A reviewer loads the supplied corpus, uploads a document, or requests a check of a catalogued official source.
2. Mitro stores the source/version metadata and hash, extracts text, and creates clause candidates for review.
3. A rule-based draft or optional Sarvam/Ollama-assisted draft can propose an engineering obligation. A reviewer checks the clause and approves or rejects the obligation.
4. Mitro scans an allowed local repository and returns candidate code locations. The output does not assert that code is compliant or non-compliant.
5. In the two supported demo cases, Mitro produces a patch proposal. Safe Patch Guard checks scope before Mitro applies the bundled patch to a separate copy and runs regression checks there.
6. Workflow events and evidence are stored locally and surfaced in the UI/API.

## Technology stack

Mitro uses a small, mostly Python-based stack:

- **Backend:** Python 3.11+, FastAPI, and Uvicorn.
- **Frontend:** HTML, CSS, and vanilla JavaScript.
- **Database:** SQLite by default; PostgreSQL can be configured.
- **AI-assisted drafting (optional):** Sarvam API or a local Ollama model.
- **Supporting libraries:** SQLAlchemy for database access, PyMuPDF and pypdf for documents, and HTTPX for HTTP requests.

### Where Sarvam AI is used

Sarvam is an **optional Phase 1 drafting provider** configured through `MITRO_LLM_PROVIDER=sarvam`. Mitro sends the selected regulatory clause text to the configured Sarvam chat-completions endpoint and treats the response as an unapproved draft. Exact quotation checks and human review remain local workflow steps. The repository scanner and Phase 3 patch templates do not send repository code to Sarvam.

Ollama is the default provider in `.env.example`. For Ollama, drafting requests remain on the local machine. Do not submit confidential or personal information to a hosted model provider.

## Quick start

### Requirements

- Windows PowerShell for the included one-command launcher, or a compatible shell for manual setup.
- Python 3.11 or newer.
- Internet access for the initial Python dependency installation. Optional hosted-source checks and Sarvam usage also require network access.

### Windows PowerShell launcher

From the project directory:

```powershell
.\run-demo.ps1
```

The script creates `.venv` if needed, installs `requirements.txt`, bootstraps the included regulatory corpus, and starts the local server at `http://127.0.0.1:8000`. Keep the terminal open while using Mitro; press `Ctrl+C` to stop it.

### Manual setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m mitro.cli bootstrap
python -m uvicorn mitro.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- Landing page: <http://127.0.0.1:8000/>
- Workbench: <http://127.0.0.1:8000/workbench>
- Interactive API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

Bootstrap is safe to repeat; identical source file hashes are deduplicated.

### Database configuration

Mitro uses a local SQLite database by default at `data/mitro.db`. To use PostgreSQL, set `MITRO_DATABASE_URL`, for example:

```text
MITRO_DATABASE_URL=postgresql+psycopg://mitro:password@localhost/mitro
```

Set environment variables in the shell or copy `.env.example` to `.env` and edit it. Do not commit `.env` or real credentials.

## Optional AI configuration

Copy the template and choose one provider. Restart Mitro after changing settings.

### Sarvam

Set these values in `.env` and replace the key with a key from your Sarvam account:

```dotenv
MITRO_LLM_PROVIDER=sarvam
MITRO_LLM_BASE_URL=https://api.sarvam.ai/v1
MITRO_LLM_API_KEY=your-sarvam-api-key
MITRO_LLM_MODEL=sarvam-105b
MITRO_LLM_API_VERSION=1
MITRO_LLM_TIMEOUT_SECONDS=90
```

Choose a model available to your account. The selected clause text is sent to Sarvam when a user requests an AI draft. AI drafting is optional; rule-based candidate drafting is available without it.

Mitro sends clause text only to the drafting provider. Repository code is not included in these drafting requests.

## Typical review workflow

1. Start Mitro and open the workbench.
2. Review the included source catalog or ingest an additional permitted source document.
3. Inspect extracted text and clause candidates against the original document. Correct extraction issues through review; scanned PDFs may require OCR.
4. Compare versions of the same source document when both versions are present.
5. Generate or write an obligation candidate, review its exact clause quotation, and approve it only when appropriate.
6. Scan the bundled Lendwise demo or register an allowed local repository. Treat all reported code locations as candidates for review.
7. For one of the two supported Phase 3 examples, inspect the proposed diff and evidence. If the change is approved for the demo, build a separate copy and run its regression checks.
8. Download the resulting ZIP if needed, and review the audit history and impact reports.

To scan a repository outside the Mitro project directory, add its parent directory to `MITRO_ALLOWED_REPO_ROOTS` using semicolon-separated paths on Windows, then restart the API:

```dotenv
MITRO_ALLOWED_REPO_ROOTS=C:\Projects;D:\Work
```

## Project structure

```text
Mitro/
├── mitro/
│   ├── api/                 # FastAPI routes and web serving
│   ├── phase1/              # Source ingestion, parsing, redlines, obligation drafts
│   ├── phase2/              # Repository scanning and impact analysis
│   ├── phase3/              # Patch scenarios, safety guard, separate-copy build
│   ├── security/            # Untrusted-content checks
│   ├── audit.py             # Workflow audit events
│   ├── dependencies.py      # Offline dependency update analysis
│   ├── database.py, db.py   # Database setup and models
│   └── cli.py               # Bootstrap command
├── amend/                   # Bundled Amend analysis engine
├── web/                     # Landing page, workbench, and design variants
├── sources/                 # Bundled documents and provenance catalog
├── targets/lendwise/        # Fictional analysis target application
├── data/                    # Local database and generated demo artifacts
├── tests/                   # Improvement-feature tests
├── run-demo.ps1             # Windows setup and launch helper
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Python package metadata
└── DEMO_GUIDE.md            # Suggested presenter walkthrough
```

## Data, privacy, and safety boundaries

- Run the local API on `127.0.0.1`; it does not provide user authentication.
- Use synthetic data only. Do not use real borrower records, credentials, or confidential production code in the demo.
- Source and database files are stored locally unless a user explicitly requests an official source fetch or a Sarvam drafting request.
- Sarvam receives selected regulatory clause text for the requested draft. Ollama runs locally. Neither provider receives repository code through the Phase 1 drafting path.
- Source-fetch URLs are constrained to configured official domains. Source refresh is manual and on demand.
- The Phase 3 builder applies only the bundled demo templates to a separate copy under `data/phase3/`; it does not modify the original Lendwise folder, push to GitHub, or deploy changes.
- Safe Patch Guard restricts file scope and patch size for supported examples. It is a deterministic demo control, not a general-purpose sandbox for arbitrary AI-generated patches.
- Human review remains necessary for source interpretation, applicability, obligations, proposed changes, and test results.

## Known limitations

- Mitro is a local prototype, has no authentication, and is not production-hardened.
- The included source set is finite. Some supplied source entries do not include exact official URLs; verify source identity, official links, and current versions before relying on them.
- Clause splitting and PDF extraction are heuristic and can mishandle columns, tables, annexes, numbering, or OCR. Always compare extracted text with the original document.
- Regulatory change matching relies substantially on citations. Renumbered, split, or merged clauses can require manual tracing.
- Candidate code mapping is static and heuristic; it is not comprehensive semantic or runtime data-flow analysis. A missing match does not prove a control exists.
- The optional prompt-injection check is pattern-based and cannot detect every malicious instruction.
- Phase 3 supports only the two named synthetic scenarios. Its tests demonstrate selected behavior; they do not establish regulatory compliance or correctness for production systems.
- Dependency analysis is offline. It does not query package registries, vulnerability databases, live release notes, or install or upgrade dependencies.
- Audit history is an application-level event log, not a tamper-proof archive.
- Lendwise is fictional. Its seeded scenarios are test fixtures, not legal findings or claims about any real lender.

## Development and verification

Install dependencies in a virtual environment, then run the API with reload enabled:

```powershell
python -m uvicorn mitro.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Run the project’s unittest suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

The built-in Phase 3 flow also runs the generated regression checks in its separate edited copy when a supported proposal is built.

For the presenter flow and sample obligation, see [DEMO_GUIDE.md](DEMO_GUIDE.md). For the local source inventory, see [sources/README.md](sources/README.md). For the fictional analysis target and its routes, see [targets/lendwise/README.md](targets/lendwise/README.md).
