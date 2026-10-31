# Mitro — India regulatory intelligence to engineering impact

Mitro is a local demo MVP for Phase 1 (regulatory intelligence), Phase 2 (code impact analysis), and a scoped Phase 3 (reviewable code-change proposals and regression evidence). It uses regulatory documents in the supplied demo database and fictional Lendwise as a synthetic target. It is not legal advice, a compliance certification, or a determination that a law has been violated.

## Included

- Phase 1: RBI/MeitY source catalog, on-demand HTTPS source checks, retained source copies, SHA-256 provenance, PDF/text extraction, clause chunking, version records, text redline, exact-quote validation, proposed obligations, and named human approval. New source versions remain reviewable; no legal conclusion is automatic.
- Phase 2: Read-only local repository registration, multi-language inventory, deterministic candidate rules, Amend's Python code graph, and explainable mapping of approved obligations to candidate files. Findings are review leads only.
- Phase 3: Select a clause and request a patch suggestion without pre-creating an obligation. The current demo has deterministic patch templates for RBI Digital Lending paragraph 10.1 (legacy consent path) and the RBI IRACP Amendment paragraph 36C (DLG cover reduction). Mitro previews a diff, creates a separate Lendwise copy, runs generated `unittest` regression checks in that copy, and offers a ZIP download.
- Synthetic target: Lendwise service with planted engineering scenarios and secure decoys.
- Storage: SQLAlchemy models with SQLite for local quickstart and PostgreSQL via MITRO_DATABASE_URL for a shared environment.
- UI/API: local review dashboard and FastAPI endpoints.
- Improvement MVPs: scoped Safe Patch Guard, evidence metadata, prompt-injection heuristics with AI abstention, regulatory version impact tracing, append-only workflow audit events, and an offline dependency update impact scan.

The included corpus has seven owner-supplied PDF copies and four owner-supplied circular text extracts. Review sources/manifest.json and sources/catalog.yaml. The manifest leaves direct source URLs blank where they were not included with a source copy. Verify and add document-specific official URLs before production use. The supplied G.S.R. 843(E) file is the DPDP Act commencement notification; the separate DPDP Rules are G.S.R. 846(E), linked in the catalog and fetchable from MeitY.

## Run locally (Windows PowerShell)

For a one-command demo setup, open PowerShell in this folder and run:

    .\run-demo.ps1

The script creates `.venv` if needed, installs dependencies, loads the included sources, and starts the web app. It needs Python 3.11+ and an internet connection for the initial package installation. Press Ctrl+C to stop the server.

For a manual setup:

    cd path\to\mitro
    py -3.11 -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m mitro.cli bootstrap
    uvicorn mitro.api.app:app --reload

Visit http://127.0.0.1:8000 for the new landing page or http://127.0.0.1:8000/workbench for the full review workspace. API docs are at /docs. Bootstrap can be repeated; identical file hashes are deduplicated. To use PostgreSQL, set MITRO_DATABASE_URL to a SQLAlchemy URL such as postgresql+psycopg://user:password@localhost/mitro.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the presenter flow and sample Lendwise obligation.

## Safety and change-impact MVPs

- **Safe Patch Guard** checks the two supported demo scenarios against explicit file allowlists, protected paths, secret-like content, and size limits before building a separate copy. Every proposed patch still requires human review.
- **Evidence metadata** ties patch proposals to the source identifier, citation, source hash, exact quotation, code files, and any linked obligations. The current direct-from-clause proposal flow may have no approved obligation linked; the interface calls this out for review.
- **Prompt-injection handling** flags a small set of instruction-like patterns in clauses and makes AI obligation drafting abstain for those clauses. This is a heuristic safeguard, not a complete prompt-injection detector. Repository code is not sent to the drafting model.
- **Regression checks** run in the existing isolated-copy workflow. A passing test describes tested behavior, not legal compliance.
- **Regulatory impact tracing** compares clauses by citation between two versions, lists linked obligations, and maps approved obligations to candidate code locations. Citation changes and clause splits/merges require manual review.
- **Audit history** is available from the workbench’s “Change & dependency impact” view and `/api/audit`. It is an application log, not a tamper-proof archive.
- **Framework/dependency analysis** scans local dependency manifests and Python imports for a manually entered proposed package version. Optional migration notes are inspected locally for review-related terms. It does not check live registries, advisories, or release-note sources and does not install or upgrade packages.

## Review flow

1. Load the included corpus, upload a source file, or fetch one explicit HTTPS source from an RBI, MeitY, or e-Gazette host.
2. Use “Check official sources now” for an on-demand check of the allow-listed catalog. Changed content is retained as a new version with its official URL and SHA-256. Review the response, extracted clauses, and original source before relying on it. Scanned PDFs are flagged for OCR or sent through the optional local Tesseract OCR path when installed.
3. Review extracted clauses. For model-assisted candidate drafting, copy `.env.example` to `.env`, configure Ollama or Sarvam, and restart the API. Ollama is local; Sarvam sends only the selected regulatory clause text to Sarvam. Repository code is not sent to either provider.
4. Compare two versions of the same source document where both have been ingested.
5. For a supported clause, select **Suggest code change**. Mitro shows the exact clause, a draft engineering interpretation, and a diff. This does not require an approved obligation first.
6. Review the diff, then select **Create separate edited copy and run test**. Mitro copies Lendwise, applies only the bundled demo patch, runs the generated regression test in that copy, and provides a ZIP download. The original Lendwise source folder is not written.
7. For clauses without a supported Phase 3 template, scan Lendwise or register another local folder and inspect Phase 2 candidate locations. For folders outside the Mitro project, add the parent directory to `MITRO_ALLOWED_REPO_ROOTS` and restart the API.
8. A qualified reviewer can then approve the obligation and applicability separately. Treat all code matches as leads for review, not compliance findings.

## Important limits

- Source monitoring is a manually triggered check of catalog URLs from RBI, MeitY, and e-Gazette allow-listed hosts; it does not crawl continuously or guarantee discovery of every new publication.
- The clause splitter is heuristic and can mishandle PDF columns, tables, annexes, numbering, or OCR. Redlines must be reviewed against the original document.
- Candidate extraction has a deterministic rule-based mode and optional Ollama or Sarvam model drafting. Exact quotes are checked locally and drafts remain proposed. It is not AI legal interpretation.
- Static rules and lexical mapping are not semantic data-flow analysis. The Amend graph is Python-centric. No match does not prove a control exists.
- Phase 3 patch generation is deliberately limited to two clause patterns in the bundled Lendwise demo. Other clauses do not receive automatic edits. Generated tests demonstrate specific synthetic expected behavior; they do not validate accounting policy or prove regulatory compliance.
- The local API has no authentication. Run only on localhost with synthetic data. Ollama stays local. Sarvam receives selected regulatory clause text only; never place borrower or confidential data in the demo.
- The prototype does not edit the original code, create pull requests, push to GitHub, or claim verified compliance. The supported Phase 3 templates write only to a separate Lendwise copy under `data/phase3/`.

## Project layout

- mitro/phase1/ — source extraction, segmentation, ingestion, redline
- mitro/phase2/ — code graph and impact candidate mapping
- mitro/phase3/ — scoped patch previews, generated tests, and separate-copy builder
- mitro/api/ and web/ — dashboard and API
- amend/ — reused deterministic Amend engine (MIT-licensed; attribution/license in THIRD_PARTY_AMEND_LICENSE)
- targets/lendwise/ — synthetic Python lending platform
- sources/ — source corpus and provenance manifests





