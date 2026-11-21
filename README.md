<div align="center">

# Mitro

### Regulatory-to-Engineering Review for Indian NBFCs

**Trace an RBI / MeitY regulatory change from the source clause to the code that may need attention, with a human reviewer at every decision point.**

`Cybersecurity Track`

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-default-003B57?logo=sqlite&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-optional-4169E1?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/status-prototype-orange)

</div>

---

## Project Links

| | |
| --- | --- |
| 🌐 **Live Project** | [mitro-r85m.onrender.com](https://mitro-r85m.onrender.com) |
| 🎬 **Video Walkthrough** | [Watch the Mitro demo on YouTube](https://youtu.be/1eMhHhTPQFU) |
| 📖 **Presenter Guide** | [DEMO_GUIDE.md](DEMO_GUIDE.md) |
| 📚 **Source Inventory** | [sources/README.md](sources/README.md) |
| 🏦 **Demo Target App** | [targets/lendwise/README.md](targets/lendwise/README.md) |

### Demo Video

[![Mitro demo video](https://img.youtube.com/vi/1eMhHhTPQFU/maxresdefault.jpg)](https://youtu.be/1eMhHhTPQFU)

> Click the thumbnail to watch the walkthrough.

> ⚠️ **Public demo notice:** The prototype has no user authentication. Do not upload non-public regulatory material, real borrower data, API keys, or company source code to the hosted instance.

---

## Overview

For an NBFC, one regulatory update can touch policies, customer journeys, operational controls **and** software. Compliance teams read the circular; engineering teams read the code; and the link between the two is usually a meeting and a spreadsheet.

**Mitro gives both teams one shared review trail:**

```
Regulatory document  →  Clause  →  Engineering obligation  →  Candidate code location  →  Reviewable patch + test evidence
```

Every step keeps its **source citation, exact clause text, file path, and review status**, so a reviewer can see how any suggestion was formed.

> **Important.** Mitro is a prototype for review and demonstration. It does **not** decide whether a regulation applies to an NBFC, determine compliance or non-compliance, or replace legal and compliance review. Code matches are *candidate locations for investigation*, not confirmed control gaps or regulatory findings. The bundled **Lendwise** platform is fictional and uses synthetic scenarios only.

## Contents

- [Who Mitro Is For](#who-mitro-is-for)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
  - [1. End-to-end view](#1-end-to-end-view)
  - [2. Organisation view (compliance & risk)](#2-organisation-view-compliance--risk)
  - [3. Software team view (engineering)](#3-software-team-view-engineering)
  - [4. Component map](#4-component-map)
  - [Data flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Typical Review Workflow](#typical-review-workflow)
- [API Overview](#api-overview)
- [Project Structure](#project-structure)
- [Security, Privacy & Safety Boundaries](#security-privacy--safety-boundaries)
- [Known Limitations](#known-limitations)
- [Development & Verification](#development--verification)

---

## Who Mitro Is For

Mitro is designed around two collaborating groups. These are intended *users of the prototype*, not authenticated roles; the local demo has no sign-in or access control.

| | 🏢 Organisation (Compliance, Risk & Assurance) | 💻 Software Team (Technology & Product) |
| --- | --- | --- |
| **Goal** | Understand what changed in a regulation and record a defensible interpretation | Find which code areas may relate to a reviewed requirement and plan the work |
| **Works with** | Source documents, clauses, redlines, obligations, approvals, audit history | Code scans, candidate locations, patch proposals, regression tests, pull requests |
| **Mitro helps by** | Cataloguing sources, extracting and comparing clauses, drafting obligations for review, tracking lifecycle states | Mapping approved obligations to code, previewing scoped changes in a separate copy, running regression checks |
| **Decides** | Applicability, obligation wording, approval | Implementation approach, merge, release |
| **Evidence they see** | Source hash, page-linked clause text, status history, audit trail | File paths, snippets, diff, test outcome, dependency impact |

---

## Key Features

### 🏢 For the organisation

- **Regulatory source catalog** – supplied RBI and MeitY document copies, cataloged with identifiers, dates and provenance metadata.
- **Document ingestion** – PDF, text, Markdown, XML and HTML uploads, plus a single explicitly supplied HTTPS URL from permitted official domains.
- **On-demand source checks** – re-check catalogued official URLs when requested, keep changed copies as new versions, and record SHA-256 hashes *(not continuous monitoring)*.
- **Clause extraction & review** – segments text into clause candidates, keeps the starting PDF page, opens the original PDF at that page, and flags cases that need OCR or manual correction.
- **Version comparison** – text redlines and clause-level changes between versions of the same document.
- **Obligation drafting & approval** – rule-based candidates or optional model-assisted drafts (Sarvam / Ollama). Drafts stay *proposals* until a human approves them.
- **Obligation lifecycle & tasks** – compliance and engineering review states with the actor and note for each change, and dated engineering tasks with blockers and completion status.
- **Audit history** – application-level log of ingestion, approval, scans, patch builds and impact analysis.

### 💻 For the software team

- **Repository registration & scanning** – register an allowed local repository or connect a GitHub App, pick an installation repository and branch, and run a **read-only** scan that surfaces candidate code locations with paths and snippets.
- **Regulatory change impact** – compare two document versions, find linked obligations, and map approved obligations to candidate code for re-review.
- **Scoped code-change examples** – preview changes for exactly two bundled Lendwise scenarios:
  - Digital Lending ¶10.1 – consent validation in a legacy-import path
  - IRACP Amendment ¶36C – DLG cover reduction after invocation
- **Safe Patch Guard** – scenario-specific file allowlists, protected paths, secret-like content checks and patch-size limits before a separate edited copy is created.
- **Regression evidence** – generated checks run in the separate copy; the outcome is retained as evidence of *tested behaviour*. Download the result as a ZIP.
- **GitHub change control** – signed webhook validation, short-lived repository-scoped installation tokens, and an optional **draft** pull request on a separate branch after an approved obligation, exact source match, passing scoped test and deterministic patch-safety check.
- **Dependency update impact** – inspect local manifests and Python imports for a manually supplied version proposal (offline; nothing is installed).
- **Amend analysis engine** – bundled engine (`amend/`) for code graph building, canary and guard checks, verification and evidence generation, with optional IBM Granite (watsonx.ai) drafting and screening.

---

## System Architecture

Mitro is a single FastAPI service with a lightweight web UI. Its workflows are organised so that the **organisation** and the **software team** each own one half of the review trail and meet at the *approved obligation*.

### 1. End-to-end view

```mermaid
flowchart TB
    subgraph Users["People"]
        direction LR
        ORG["🏢 Organisation<br/>Compliance · Risk · Assurance"]
        DEV["💻 Software team<br/>Engineering · Product"]
    end

    UI["Mitro web UI<br/>HTML · CSS · vanilla JavaScript<br/>Landing page + Workbench"]
    API["FastAPI application<br/>REST API + OpenAPI docs"]

    ORG --> UI
    DEV --> UI
    UI -->|HTTP| API

    subgraph Workflows["Mitro workflows"]
        direction LR
        P1["Phase 1<br/>Regulatory intelligence<br/>Ingest · extract · compare · draft"]
        P2["Phase 2<br/>Code impact analysis<br/>Scan · map candidate locations"]
        P3["Phase 3<br/>Code-change demo<br/>Propose · guard · test copy"]
        P4["Change impact<br/>Version diff · dependencies"]
    end

    API --> P1
    API --> P2
    API --> P3
    API --> P4

    subgraph Inputs["Sources and targets"]
        direction LR
        CORPUS["Local source corpus<br/>+ uploaded documents"]
        OFFICIAL["Allow-listed official URLs<br/>(checked on request)"]
        REPO["Allowed local repository<br/>or GitHub App repo<br/>(Lendwise by default)"]
    end

    subgraph Storage["Local project data"]
        direction LR
        DB[("SQLAlchemy database<br/>SQLite default · PostgreSQL optional")]
        COPIES["Separate edited copies<br/>tests · evidence · ZIPs"]
        AUDIT["Workflow audit events"]
    end

    subgraph AI["Optional drafting providers"]
        direction LR
        SARVAM["Sarvam API<br/>clause text only"]
        OLLAMA["Ollama<br/>local model"]
    end

    P1 --> CORPUS
    P1 -->|manual check| OFFICIAL
    P1 -->|documents · clauses · obligations| DB
    P1 -.->|optional draft| SARVAM
    P1 -.->|optional draft| OLLAMA
    P2 -->|read-only scan| REPO
    P2 -->|candidate locations| DB
    P3 -->|read source copy| REPO
    P3 -->|guarded build + tests| COPIES
    P3 -->|proposal + evidence| DB
    P4 -->|compare / map| DB
    API -->|record actions| AUDIT --> DB
```

### 2. Organisation view (compliance & risk)

*What the compliance side does, and where a human decision is required.*

```mermaid
flowchart LR
    A["📄 Regulatory source<br/>RBI / MeitY document"] --> B["Ingest<br/>upload · catalog · official URL"]
    B --> C["Hash + version<br/>SHA-256 stored"]
    C --> D["Extract clauses<br/>page-linked, OCR-flagged"]
    D --> E["Compare versions<br/>redline + clause changes"]
    D --> F["Draft obligation<br/>rule-based or Sarvam/Ollama"]
    F --> G{{"👤 Reviewer<br/>checks exact clause quote"}}
    G -->|approve| H["Approved obligation<br/>lifecycle + status history"]
    G -->|reject / revise| F
    H --> I["Engineering task<br/>owner · due date · blockers"]
    H --> J["Audit trail<br/>who · what · when"]
    E --> K["Regulatory change impact<br/>linked obligations to re-review"]
    K --> G

    classDef human fill:#fff4d6,stroke:#c98a00,color:#000;
    class G human;
```

### 3. Software team view (engineering)

*What the engineering side does with an approved obligation.*

```mermaid
flowchart LR
    A["✅ Approved obligation<br/>from compliance review"] --> B["Select repository<br/>local folder or GitHub App branch"]
    B --> C["Read-only scan<br/>multi-language patterns + code graph"]
    C --> D["Candidate code locations<br/>path · snippet · reason"]
    D --> E{{"👨‍💻 Engineer<br/>reviews candidates"}}
    E --> F["Suggest code change<br/>(2 supported scenarios)"]
    F --> G["🛡️ Safe Patch Guard<br/>allowlist · protected paths<br/>secret check · size limit"]
    G -->|pass| H["Build separate copy<br/>original is never modified"]
    G -->|fail| X["Blocked"]
    H --> I["Run generated<br/>regression test"]
    I --> J["Evidence + ZIP download"]
    J --> K{{"Engineer approves"}}
    K -->|optional, flag enabled| L["Draft PR on codex/mitro-obligation-*<br/>never pushes to default branch · never merges"]

    classDef human fill:#fff4d6,stroke:#c98a00,color:#000;
    classDef guard fill:#e6f4ea,stroke:#2e7d32,color:#000;
    class E,K human;
    class G guard;
```

### 4. Component map

```mermaid
flowchart TB
    subgraph web["web/"]
        HOME["home.html<br/>landing page"]
        WB["index.html<br/>workbench"]
    end

    subgraph mitro["mitro/"]
        APP["api/app.py<br/>routes + static serving"]
        GH["github_app.py<br/>App auth · webhooks · draft PRs"]
        DEPS["dependencies.py<br/>offline dependency impact"]
        SEC["security/untrusted.py<br/>prompt-injection pattern check"]
        AUD["audit.py"]
        DBM["database.py · db.py<br/>models + setup"]
        subgraph p1["phase1/"]
            ING["ingest.py"]
            PAR["parser.py"]
            RED["redline.py"]
            MON["monitor.py"]
            AID["ai_draft.py"]
        end
        subgraph p2["phase2/"]
            SCN["scanner.py"]
        end
        subgraph p3["phase3/"]
            CHG["changes.py"]
            SAF["safety.py"]
            BLD["build_copy.py"]
        end
    end

    subgraph amend["amend/"]
        GRA["graph.py · canary.py · guard.py"]
        VER["verify.py · evidence.py"]
        WAT["watsonx.py · draft.py · screen.py"]
    end

    subgraph data["Data"]
        SRC["sources/<br/>PDFs · catalog.yaml · manifest.json"]
        TGT["targets/lendwise/<br/>fictional NBFC app"]
        GEN["data/<br/>mitro.db · phase3 copies"]
    end

    HOME --> APP
    WB --> APP
    APP --> p1
    APP --> p2
    APP --> p3
    APP --> GH
    APP --> DEPS
    APP --> AUD --> DBM
    p1 --> SRC
    p1 --> SEC
    p2 --> TGT
    p2 --> GRA
    p3 --> TGT
    p3 --> GEN
    p1 --> DBM
```

### Data flow

1. A reviewer loads the supplied corpus, uploads a document, or requests a check of a catalogued official source.
2. Mitro stores source/version metadata and hash, extracts text, and creates clause candidates.
3. A rule-based or optional Sarvam/Ollama draft proposes an engineering obligation. A reviewer checks the clause and approves or rejects it.
4. Mitro scans an allowed repository (read-only) and returns **candidate** code locations. It never asserts code is compliant or non-compliant.
5. For the two supported demo cases, Mitro produces a patch proposal. Safe Patch Guard checks scope, Mitro applies the bundled patch to a **separate copy**, and regression checks run there.
6. Workflow events and evidence are stored locally and surfaced in the UI/API.

---

## Technology Stack

| Layer | Technology |
| --- | --- |
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Frontend** | HTML, CSS, vanilla JavaScript |
| **Database** | SQLAlchemy · SQLite (default) · PostgreSQL (optional, `psycopg`) |
| **Documents** | PyMuPDF, pypdf; optional Docling, OCRmyPDF, PaddleOCR |
| **Code analysis** | NetworkX (code graph), sqlglot (SQL), YAML-driven scenario catalogs |
| **HTTP / auth** | HTTPX, PyJWT (GitHub App) |
| **Optional AI drafting** | Sarvam API · local Ollama · IBM Granite on watsonx.ai (Amend engine) |

### Where AI is used

In the Mitro review workflow, AI drafting is **optional**. Selected regulatory clause text is sent to the configured drafting provider and the response is treated as an **unapproved draft**. Exact-quotation checks and human review remain part of the workflow. The bundled `amend/` engine has separate optional IBM watsonx.ai integrations for drafting and screening. The repository scanner and Phase 3 patch templates are deterministic; Mitro does not send repository code to Sarvam or Ollama for obligation drafting.

---

## Quick Start

### Requirements

- Python **3.11+**
- Windows PowerShell for the one-command launcher (or a compatible shell for manual setup)
- Internet access for the first dependency install (and for optional hosted-source checks / Sarvam)

### Option A — One command (Windows)

```powershell
.\run-demo.ps1
```

This creates `.venv`, installs `requirements.txt`, bootstraps the regulatory corpus, and starts the server at `http://127.0.0.1:8000`. Press `Ctrl+C` to stop.

### Option B — Manual setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m mitro.cli bootstrap
python -m uvicorn mitro.api.app:app --host 127.0.0.1 --port 8000 --reload
```

| Page | URL |
| --- | --- |
| Landing page | <http://127.0.0.1:8000/> |
| Workbench | <http://127.0.0.1:8000/workbench> |
| API docs (Swagger) | <http://127.0.0.1:8000/docs> |
| Health check | <http://127.0.0.1:8000/health> |

Bootstrap is safe to repeat; identical source hashes are de-duplicated.

---

## Configuration

Copy `.env.example` to `.env`, edit, and restart Mitro. **Never commit `.env` or real credentials.**

<details>
<summary><b>Database</b></summary>

SQLite is used by default at `data/mitro.db`. For PostgreSQL:

```dotenv
MITRO_DATABASE_URL=postgresql+psycopg://mitro:password@localhost/mitro
```
</details>

<details>
<summary><b>AI drafting — Ollama (default, local)</b></summary>

```dotenv
MITRO_LLM_PROVIDER=ollama
MITRO_LLM_BASE_URL=http://127.0.0.1:11434/v1
MITRO_LLM_MODEL=qwen2.5
MITRO_LLM_TIMEOUT_SECONDS=90
```
Run `ollama pull qwen2.5` first. Clause text stays on your machine.
</details>

<details>
<summary><b>AI drafting — Sarvam (hosted)</b></summary>

```dotenv
MITRO_LLM_PROVIDER=sarvam
MITRO_LLM_BASE_URL=https://api.sarvam.ai/v1
MITRO_LLM_API_KEY=your-sarvam-api-key
MITRO_LLM_MODEL=sarvam-105b
MITRO_LLM_API_VERSION=1
MITRO_LLM_TIMEOUT_SECONDS=90
```
Choose a model enabled for your account. Selected clause text is sent to Sarvam when a user requests an AI draft. Do not submit confidential or personal information.
</details>

<details>
<summary><b>Scanning repositories outside the project</b></summary>

```dotenv
MITRO_ALLOWED_REPO_ROOTS=C:\Projects;D:\Work
```
Separate paths with `;` on Windows. Restart the API after changing.
</details>

<details>
<summary><b>GitHub App (optional)</b></summary>

```dotenv
MITRO_GITHUB_APP_ID=your-app-id
MITRO_GITHUB_APP_SLUG=your-app-slug
MITRO_GITHUB_PRIVATE_KEY_PATH=C:\secrets\mitro-app.pem
MITRO_GITHUB_WEBHOOK_SECRET=your-long-random-webhook-secret
MITRO_GITHUB_ENABLE_PULL_REQUESTS=false
```

- **Setup URL:** `http://127.0.0.1:8000/api/github/callback`
- **Webhook URL:** `http://127.0.0.1:8000/api/github/webhook` (needs a public HTTPS URL to receive remote deliveries)
- **Permissions:** start with *Metadata: read* + *Contents: read*; subscribe to `push` and `pull_request`
- **Flow:** open `/api/github/connect` → install the App → pick repository and branch → scan
- **Draft PRs (off by default):** grant *Contents: write* and *Pull requests: write*, review the obligation and patch, pass the scoped scenario test, then set `MITRO_GITHUB_ENABLE_PULL_REQUESTS=true`. Mitro opens a draft PR from a separate `codex/mitro-obligation-*` branch. It never pushes to the default branch and never merges. The PR states that target-repository tests were **not run**.
</details>

<details>
<summary><b>Optional PDF engines</b></summary>

Install the optional packages individually in the same Python environment when needed: `docling`, `ocrmypdf`, or `paddleocr`. Docling can produce structured document and Markdown artifacts; OCRmyPDF handles low-text PDFs with rotation and deskew and may require Tesseract; PaddleOCR is a fallback. PyMuPDF and pypdf remain the core PDF parsers. OCR output is marked for human verification. These optional packages are not included in `requirements.txt`.
</details>

---

## Typical Review Workflow

| # | Step | Owner |
| --- | --- | --- |
| 1 | Start Mitro and open the workbench | Either |
| 2 | Review the source catalog or ingest an additional permitted document | 🏢 Organisation |
| 3 | Inspect extracted text and clauses against the original PDF; correct extraction issues | 🏢 Organisation |
| 4 | Compare versions of the same document when both are present | 🏢 Organisation |
| 5 | Draft an obligation, check the exact clause quote, approve only when appropriate | 🏢 Organisation |
| 6 | Scan Lendwise or an allowed repository; treat results as candidates | 💻 Software team |
| 7 | For a supported scenario, inspect the diff, build a separate copy, run regression checks | 💻 Software team |
| 8 | Download the ZIP; review audit history and impact reports | Both |

### Five-minute demo path

1. Open **RBI NBFC IRACP Amendment Directions, 2026 – DLG provisioning** → clause **36C**.
2. Click **Suggest code change** → Mitro points to `app/services/provisioning.py` and shows the diff.
3. Click **Create separate edited copy and run test**.
4. Download the edited Lendwise ZIP.
5. If time permits, repeat with **Digital Lending ¶10.1** (legacy-import consent).

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for presenter notes.

---

## API Overview

Interactive docs are available at `/docs`. Main route groups:

| Area | Representative endpoints |
| --- | --- |
| **Health** | `GET /health` · `GET /api/health` |
| **Sources & ingestion** | `GET /api/sources` · `POST /api/sources/refresh` · `POST /api/ingest` · `POST /api/ingest-url` · `POST /api/bootstrap` |
| **Documents & clauses** | `GET /api/documents` · `GET /api/versions/{id}/clauses` · `GET /api/versions/{id}/pdf` · `GET /api/redline` |
| **Obligations** | `GET/POST /api/obligations` · `POST /api/ai-draft/{version_id}` · `POST /api/obligations/{id}/approve` · `POST /api/obligations/{id}/status` · `GET/POST /api/obligations/{id}/tasks` |
| **Code impact** | `POST /api/scan` · `GET /api/impact/{obligation_id}` · `GET/POST /api/repositories` |
| **Phase 3 (code change)** | `POST /api/phase3/proposals` · `POST /api/phase3/proposals/{id}/build` · `GET /api/phase3/proposals/{id}/download` |
| **Change impact** | `GET /api/versions/{old}/impact/{new}` · `POST /api/dependencies/analyze` |
| **GitHub** | `GET /api/github/status` · `GET /api/github/connect` · `POST /api/github/webhook` · `POST /api/github/repositories/{id}/scan` · `POST /api/github/proposals/{id}/pull-request` |
| **Audit** | `GET /api/audit` |

---

## Project Structure

```text
Mitro/
├── mitro/                      # Core application
│   ├── api/                    #   FastAPI routes + web serving
│   ├── phase1/                 #   Ingestion, parsing, redlines, monitoring, AI drafts
│   ├── phase2/                 #   Repository scanning + impact analysis
│   ├── phase3/                 #   Patch scenarios, safety guard, separate-copy build
│   ├── security/               #   Untrusted-content checks
│   ├── github_app.py           #   GitHub App auth, webhooks, draft PRs
│   ├── dependencies.py         #   Offline dependency impact analysis
│   ├── audit.py                #   Workflow audit events
│   ├── database.py, db.py      #   Database setup and models
│   └── cli.py                  #   `bootstrap` command
├── amend/                      # Bundled analysis engine (graph, canary, guard, verify, evidence)
├── web/                        # Landing page + workbench + design variants
├── design/                     # UI concepts, previews and style experiments
├── sources/                    # Regulatory PDFs/text, catalog.yaml, manifest.json
├── targets/lendwise/           # Fictional NBFC target application
├── data/                       # Local DB and generated Phase 3 artifacts
├── tests/                      # Test suite
├── run-demo.ps1                # Windows setup + launch helper
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Package metadata
├── DEMO_GUIDE.md               # Presenter walkthrough
└── DESIGN.md                   # Design notes
```

---

## Security, Privacy & Safety Boundaries

- Run the API on `127.0.0.1`. There is **no user authentication**.
- Use **synthetic data only** — no real borrower records, credentials, or confidential production code.
- Data stays local unless a user explicitly requests an official-source fetch or a Sarvam draft.
- Source-fetch URLs are limited to configured official domains; refresh is manual.
- Sarvam receives only selected clause text. Ollama runs locally. Neither receives repository code.
- The Phase 3 builder applies **bundled templates to a separate copy** under `data/phase3/`. It does not modify the original Lendwise folder or deploy anything.
- GitHub integration uses short-lived, repository-scoped installation tokens that are **not stored**. Pull requests are **off by default**, always **draft**, and never merge.
- Safe Patch Guard is a deterministic demo control, **not** a general-purpose sandbox for arbitrary AI-generated patches.
- Human review remains necessary for interpretation, applicability, obligations, proposed changes and test results.

---

## Known Limitations

- Local prototype: no authentication, roles, notifications or organisation isolation; not production-hardened.
- The source set is finite; some entries lack exact official URLs. Verify identity, links and current versions before relying on them.
- Clause splitting and PDF extraction are heuristic (columns, tables, annexes, numbering, OCR). Always compare against the original.
- Synchronized side-by-side PDF review is not implemented.
- Regulatory change matching leans on citations; renumbered, split or merged clauses may need manual tracing.
- Code mapping is static and heuristic, not semantic or runtime data-flow analysis. A missing match does not prove a control exists.
- Prompt-injection screening is pattern-based and cannot catch every malicious instruction.
- Phase 3 supports only **two** named synthetic scenarios; its tests do not establish regulatory compliance or production correctness.
- Pull-request checks run the bundled scenario test, not the connected repository's own tests — run those before merging.
- Dependency analysis is offline (no registry or vulnerability database lookups).
- Audit history is an application-level log, not a tamper-proof archive.
- Lendwise is fictional; its scenarios are test fixtures, not findings about any real lender.

---

## Development & Verification

```powershell
# Run with auto-reload
python -m uvicorn mitro.api.app:app --host 127.0.0.1 --port 8000 --reload

# Run the test suite
python -m unittest discover -s tests -v
```

The Phase 3 flow also runs its generated regression checks inside the separate edited copy whenever a supported proposal is built.

---

<div align="center">

**Mitro** — a shared, evidence-backed review trail between compliance and engineering.

*Prototype for review and demonstration. Not legal advice. Human review required.*

</div>
