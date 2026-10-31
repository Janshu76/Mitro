from datetime import datetime, timezone
import os
from pathlib import Path
import uuid
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from mitro.database import get_db, ROOT, DATA_DIR
from mitro.db import RegulatoryDocument, DocumentVersion, Clause, Obligation, RepositoryScan, SourceCheck, CodeRepository, CodeChangeProposal
from mitro.phase1.ingest import ingest_file, bootstrap
from mitro.phase1.redline import redline
from mitro.phase2.scanner import scan_repository, impact_candidates
from mitro.phase1.monitor import refresh_official_sources
from mitro.phase3.changes import build_change
from mitro.phase3.build_copy import build_and_verify

def _catalog_source_url(identifier: str) -> str:
    import yaml
    catalog = yaml.safe_load((ROOT / "sources" / "catalog.yaml").read_text(encoding="utf-8-sig")) or {}
    return next((str(item.get("official_url", "")) for item in catalog.get("sources", [])
                 if item.get("identifier") == identifier), "")

app = FastAPI(title="Mitro", version="0.1.0", description="India regulatory intelligence and code impact analysis MVP")

class ObligationIn(BaseModel):
    clause_id: int
    key: str = Field(min_length=2, max_length=80)
    quote: str = Field(min_length=8)
    statement: str = Field(min_length=10)
    engineering_shape: str = "code"

class ApprovalIn(BaseModel):
    approver: str = Field(min_length=2)
    reviewer_note: str = ""

class RepositoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    path: str = Field(min_length=3, max_length=2000)

def _allowed_roots() -> list[Path]:
    roots = [ROOT.resolve()]
    for raw in os.getenv("MITRO_ALLOWED_REPO_ROOTS", "").split(os.pathsep):
        if raw.strip():
            roots.append(Path(raw.strip()).expanduser().resolve())
    return roots

def _repository_path(repository: str, repository_id: int | None, db: Session) -> Path:
    if repository_id is not None:
        if repository_id == 0:
            path = (ROOT / "targets" / "lendwise").resolve()
        else:
            repo = db.get(CodeRepository, repository_id)
            if not repo:
                raise HTTPException(404, "Registered repository not found")
            path = Path(repo.root_path).resolve()
    else:
        path = (ROOT / repository).resolve()
    if not path.exists() or not path.is_dir() or not any(path.is_relative_to(root) for root in _allowed_roots()):
        raise HTTPException(400, "Repository must be an existing directory within Mitro or MITRO_ALLOWED_REPO_ROOTS")
    return path

@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "project": "Mitro", "environment": "local-demo"}

@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.scalars(select(RegulatoryDocument).order_by(RegulatoryDocument.id)).all()
    return [{"id": d.id, "regulator": d.regulator, "identifier": d.identifier, "title": d.title,
             "source_url": d.source_url, "versions": [{"id": v.id, "date": v.version_date,
             "file": v.source_filename, "hash": v.sha256, "extraction": v.extraction_method,
             "clauses": len(v.clauses)} for v in d.versions]} for d in docs]

@app.get("/api/sources")
def list_sources(db: Session = Depends(get_db)):
    import yaml
    catalog = yaml.safe_load((ROOT / "sources" / "catalog.yaml").read_text(encoding="utf-8-sig")) or {}
    out = []
    for item in catalog.get("sources", []):
        latest = db.scalar(select(SourceCheck).where(SourceCheck.source_id == item["id"]).order_by(SourceCheck.id.desc()))
        out.append({**item, "last_check": ({"checked_at": latest.checked_at, "outcome": latest.outcome,
                    "http_status": latest.http_status, "version_id": latest.version_id, "detail": latest.detail} if latest else None)})
    return out

@app.post("/api/sources/refresh")
async def refresh_sources(db: Session = Depends(get_db)):
    try:
        return await refresh_official_sources(db)
    except Exception as exc:
        raise HTTPException(502, f"Source check failed: {exc}") from exc

@app.get("/api/sources/{source_id}/checks")
def source_check_history(source_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(SourceCheck).where(SourceCheck.source_id == source_id).order_by(SourceCheck.id.desc()).limit(20)).all()
    return [{"checked_at": r.checked_at, "outcome": r.outcome, "http_status": r.http_status,
             "sha256": r.sha256, "version_id": r.version_id, "detail": r.detail} for r in rows]

@app.get("/api/repositories")
def list_repositories(db: Session = Depends(get_db)):
    repos = db.scalars(select(CodeRepository).order_by(CodeRepository.id)).all()
    return [{"id": 0, "name": "Lendwise demo", "built_in": True}] + [
        {"id": r.id, "name": r.name, "built_in": False} for r in repos]

@app.post("/api/repositories")
def register_repository(body: RepositoryIn, db: Session = Depends(get_db)):
    path = Path(body.path).expanduser().resolve()
    if not path.exists() or not path.is_dir() or not any(path.is_relative_to(root) for root in _allowed_roots()):
        raise HTTPException(400, "Choose an existing folder under the Mitro project or a configured MITRO_ALLOWED_REPO_ROOTS directory")
    existing = db.scalar(select(CodeRepository).where(CodeRepository.root_path == str(path)))
    if existing:
        return {"id": existing.id, "name": existing.name, "message": "Folder already registered"}
    repo = CodeRepository(name=body.name.strip(), root_path=str(path), source_kind="local_path",
                          created_at=datetime.now(timezone.utc).isoformat())
    db.add(repo); db.commit(); db.refresh(repo)
    return {"id": repo.id, "name": repo.name, "message": "Registered for read-only local scanning"}

@app.post("/api/ingest")
async def upload_document(file: UploadFile = File(...), identifier: str = Form(...), title: str = Form(...),
        version_date: str = Form(...), publication_date: str = Form(""), source_url: str = Form(""),
        regulator: str = Form("RBI"), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md", ".xml", ".html"}:
        raise HTTPException(415, "Upload PDF, TXT, MD, XML or HTML")
    safe_name = Path(file.filename or ("source" + suffix)).name
    target = DATA_DIR / "raw" / (uuid.uuid4().hex[:12] + "-" + safe_name)
    target.write_bytes(await file.read())
    try:
        return ingest_file(db, target, {"regulator": regulator, "identifier": identifier, "title": title,
             "version_date": version_date, "publication_date": publication_date, "source_url": source_url,
             "source_kind": "uploaded"})
    except Exception as exc:
        raise HTTPException(400, f"Ingestion failed: {exc}") from exc

@app.post("/api/ingest-url")
async def ingest_official_url(url: str = Form(...), identifier: str = Form(...), title: str = Form(...),
        version_date: str = Form(...), publication_date: str = Form(""), regulator: str = Form("RBI"),
        db: Session = Depends(get_db)):
    """Fetch one explicitly submitted public document from a small official-domain allowlist."""
    from urllib.parse import urlparse
    import httpx
    parsed = urlparse(url)
    allowed = {"rbi.org.in", "www.rbi.org.in", "website.rbi.org.in",
               "meity.gov.in", "www.meity.gov.in", "egazette.gov.in"}
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in allowed or parsed.port not in (None, 443) or parsed.username or parsed.password:
        raise HTTPException(400, "Only HTTPS URLs on RBI, MeitY, or e-Gazette hosts are allowed")
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=False) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Source fetch failed: {exc}") from exc
    if response.is_redirect or response.status_code >= 400:
        raise HTTPException(502, f"Source returned HTTP {response.status_code}; redirects are not followed")
    body = response.content
    if len(body) > 25 * 1024 * 1024:
        raise HTTPException(413, "Source exceeds 25 MB limit")
    ctype = response.headers.get("content-type", "").lower()
    path_suffix = Path(parsed.path).suffix.lower()
    suffix = path_suffix if path_suffix in {".pdf", ".txt", ".xml", ".html"} else (
        ".pdf" if "pdf" in ctype else ".html" if "html" in ctype else ".txt")
    target = DATA_DIR / "raw" / (uuid.uuid4().hex[:12] + suffix)
    target.write_bytes(body)
    try:
        return ingest_file(db, target, {"regulator": regulator, "identifier": identifier, "title": title,
             "version_date": version_date, "publication_date": publication_date, "source_url": url,
             "source_kind": "fetched_official_source"})
    except Exception as exc:
        raise HTTPException(400, f"Fetched file could not be ingested: {exc}") from exc
@app.post("/api/bootstrap")
def bootstrap_sources(db: Session = Depends(get_db)):
    try:
        return {"ingested": bootstrap(db)}
    except Exception as exc:
        raise HTTPException(400, f"Bootstrap failed: {exc}") from exc

@app.post("/api/demo/prepare")
def prepare_demo_obligation(db: Session = Depends(get_db)):
    """Create an idempotent, unapproved sample obligation for the Lendwise walkthrough."""
    key = "DEMO-VENDOR-01"
    existing = db.scalar(select(Obligation).where(Obligation.key == key))
    if existing:
        return {"id": existing.id, "key": existing.key, "status": existing.status,
                "message": "The sample obligation is already in the review list."}

    document = db.scalar(select(RegulatoryDocument).where(
        RegulatoryDocument.identifier == "RBI/DoS/2026-27/461"))
    if not document:
        raise HTTPException(409, "Load the included regulatory documents first, then prepare the sample.")
    version_ids = select(DocumentVersion.id).where(DocumentVersion.document_id == document.id)
    clause = db.scalar(select(Clause).where(Clause.version_id.in_(version_ids), Clause.citation == "117"))
    if not clause:
        raise HTTPException(409, "The included RBI cybersecurity source does not contain the expected clause 117.")

    obligation = Obligation(
        clause_id=clause.id,
        key=key,
        quote=clause.text,
        statement=("Demo review: assess vendor risk and customer-data controls for the Lendwise "
                   "KYC provider integration, including the outbound TLS configuration."),
        engineering_shape="code",
        status="proposed",
        reviewer_note="Illustrative mapping for the synthetic Lendwise demo; applicability requires human review.",
    )
    db.add(obligation)
    db.commit()
    db.refresh(obligation)
    return {"id": obligation.id, "key": obligation.key, "status": obligation.status,
            "citation": clause.citation,
            "message": "Sample created as proposed. Review and approve it before mapping it to code."}

@app.get("/api/versions/{version_id}/clauses")
def list_clauses(version_id: int, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version: raise HTTPException(404, "Version not found")
    clauses = db.scalars(select(Clause).where(Clause.version_id == version_id).order_by(Clause.ordinal)).all()
    return [{"id": c.id, "citation": c.citation, "text": c.text} for c in clauses]

@app.get("/api/redline")
def get_redline(old_version_id: int, new_version_id: int, db: Session = Depends(get_db)):
    try: return redline(db, old_version_id, new_version_id)
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc

@app.get("/api/draft-obligations/{version_id}")
def draft_obligations(version_id: int, db: Session = Depends(get_db)):
    """Return quote-grounded rule-based candidates; never approve them automatically."""
    version = db.get(DocumentVersion, version_id)
    if not version: raise HTTPException(404, "Version not found")
    clauses = db.scalars(select(Clause).where(Clause.version_id == version_id).order_by(Clause.ordinal)).all()
    out = []
    for clause in clauses:
        if not any(token in clause.text.lower() for token in ("shall", "must", "is required to", "are required to")):
            continue
        quote = clause.text[:600]
        out.append({"clause_id": clause.id, "citation": clause.citation, "quote": quote,
                    "suggested_statement": "Review this clause and describe the system or process action it requires.",
                    "status": "candidate_only", "review_required": True})
    return {"version_id": version.id, "candidates": out,
            "note": "Rule-based clause candidates are not legal interpretations. Human review and approval are required."}

@app.post("/api/ai-draft/{version_id}")
async def ai_draft_obligations(version_id: int, db: Session = Depends(get_db)):
    from mitro.phase1.ai_draft import draft_for_version
    try:
        return await draft_for_version(db, version_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Drafting provider error: {exc}") from exc
@app.post("/api/obligations")
def create_obligation(body: ObligationIn, db: Session = Depends(get_db)):
    clause = db.get(Clause, body.clause_id)
    if not clause: raise HTTPException(404, "Clause not found")
    if body.quote not in clause.text:
        raise HTTPException(422, "Quote must be an exact verbatim substring of the cited clause")
    ob = Obligation(clause_id=clause.id, key=body.key, quote=body.quote, statement=body.statement,
                    engineering_shape=body.engineering_shape, status="proposed")
    db.add(ob); db.commit(); db.refresh(ob)
    return {"id": ob.id, "key": ob.key, "status": ob.status}

@app.get("/api/obligations")
def list_obligations(db: Session = Depends(get_db)):
    obs = db.scalars(select(Obligation).order_by(Obligation.id)).all()
    return [{"id": o.id, "key": o.key, "clause_id": o.clause_id, "quote": o.quote,
             "statement": o.statement, "shape": o.engineering_shape, "status": o.status,
             "approved_by": o.approved_by} for o in obs]

@app.post("/api/obligations/{obligation_id}/approve")
def approve_obligation(obligation_id: int, body: ApprovalIn, db: Session = Depends(get_db)):
    ob = db.get(Obligation, obligation_id)
    if not ob: raise HTTPException(404, "Obligation not found")
    ob.status = "approved"; ob.approved_by = body.approver
    ob.approved_at = datetime.now(timezone.utc).isoformat(); ob.reviewer_note = body.reviewer_note
    db.commit()
    return {"id": ob.id, "status": ob.status, "approved_by": ob.approved_by}

def _proposal_json(proposal: CodeChangeProposal) -> dict:
    clause = proposal.clause_id
    return {"id": proposal.id, "clause_id": clause, "scenario": proposal.scenario,
            "source_citation": proposal.source_citation or "", "source_identifier": proposal.source_identifier or "",
            "source_url": proposal.source_url or "", "source_sha256": proposal.source_sha256 or "",
            "title": proposal.title, "quote": proposal.quote, "statement": proposal.statement,
            "expected_behavior": proposal.expected_behavior, "rationale": proposal.rationale,
            "diff": proposal.diff, "test_status": proposal.test_status,
            "test_output": proposal.test_output, "copy_ready": bool(proposal.bundle_path),
            "download_url": f"/api/phase3/proposals/{proposal.id}/download" if proposal.bundle_path else "",
            "created_at": proposal.created_at}

@app.post("/api/phase3/proposals")
def propose_code_change(clause_id: int, db: Session = Depends(get_db)):
    """Read a selected clause and draft a supported Lendwise change without prior obligation approval."""
    clause = db.get(Clause, clause_id)
    if not clause:
        raise HTTPException(404, "Clause not found")
    try:
        draft = build_change(clause.text, clause.citation)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    version = clause.version
    proposal = CodeChangeProposal(clause_id=clause.id, source_citation=clause.citation,
        source_identifier=version.document.identifier, source_url=version.provenance.get("source_url", "") or version.document.source_url or _catalog_source_url(version.document.identifier),
        source_sha256=version.sha256, scenario=draft["scenario"], title=draft["title"],
        quote=clause.text, statement=draft["rationale"], expected_behavior=draft["expected_behavior"],
        rationale=draft["rationale"], edits=draft["edits"], diff=draft["diff"],
        test_source=draft["test_source"], test_status="not_run",
        created_at=datetime.now(timezone.utc).isoformat())
    db.add(proposal); db.commit(); db.refresh(proposal)
    return {**_proposal_json(proposal), "method": draft["method"], "limitations": draft["limitations"],
            "message": "Draft only. Review the clause, interpretation, and diff before building the separate copy."}

@app.get("/api/phase3/proposals/{proposal_id}")
def get_code_change_proposal(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(CodeChangeProposal, proposal_id)
    if not proposal:
        raise HTTPException(404, "Code change proposal not found")
    return _proposal_json(proposal)

@app.post("/api/phase3/proposals/{proposal_id}/build")
def build_proposed_copy(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(CodeChangeProposal, proposal_id)
    if not proposal:
        raise HTTPException(404, "Code change proposal not found")
    try:
        result = build_and_verify(proposal, proposal.id)
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        raise HTTPException(409, str(exc)) from exc
    proposal.test_status = result["test_status"]
    proposal.test_output = result["test_output"]
    proposal.copy_path = result["copy_path"]
    proposal.bundle_path = result.get("bundle_path", proposal.bundle_path)
    db.commit()
    return {**_proposal_json(proposal), "test_output": result["test_output"],
            "message": "A separate Lendwise copy was created. The original source folder was not changed."}

@app.get("/api/phase3/proposals/{proposal_id}/download")
def download_proposed_copy(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(CodeChangeProposal, proposal_id)
    if not proposal:
        raise HTTPException(404, "Code change proposal not found")
    expected = (DATA_DIR / "phase3" / "downloads" / f"lendwise-edited-{proposal_id}.zip").resolve()
    if not proposal.bundle_path or Path(proposal.bundle_path).resolve() != expected or not expected.is_file():
        raise HTTPException(409, "Build the separate copy before downloading it")
    return FileResponse(expected, media_type="application/zip", filename=f"lendwise-edited-{proposal_id}.zip")

@app.post("/api/scan")
def scan_target(repository: str = "targets/lendwise", repository_id: int | None = None, db: Session = Depends(get_db)):
    path = _repository_path(repository, repository_id, db)
    try: summary = scan_repository(path)
    except Exception as exc: raise HTTPException(400, f"Scan failed: {exc}") from exc
    scan = RepositoryScan(repository_path=str(path), scanned_at=datetime.now(timezone.utc).isoformat(),
                          engine="Amend Python code graph + Mitro keyword mapper", summary=summary)
    db.add(scan); db.commit(); db.refresh(scan)
    return {"scan_id": scan.id, **summary}

@app.get("/api/impact/{obligation_id}")
def obligation_impact(obligation_id: int, repository: str = "targets/lendwise", repository_id: int | None = None, db: Session = Depends(get_db)):
    ob = db.get(Obligation, obligation_id)
    if not ob: raise HTTPException(404, "Obligation not found")
    clause = db.get(Clause, ob.clause_id)
    if ob.status != "approved":
        return {"obligation_id": ob.id, "status": ob.status, "candidate_code_locations": [],
                "message": "Approve the obligation before mapping it to code."}
    path = _repository_path(repository, repository_id, db)
    return {"obligation_id": ob.id, "status": ob.status,
            "candidate_code_locations": impact_candidates(path, ob.statement, ob.quote, clause.citation),
            "interpretation": "Candidate locations for human review; not a regulatory finding."}

app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "web" / "index.html")




