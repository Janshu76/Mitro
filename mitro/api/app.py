from datetime import datetime, timezone
import os
from pathlib import Path
import uuid
import json
import zipfile
import tempfile
import io
import base64
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from mitro.database import get_db, ROOT, DATA_DIR
from mitro.db import RegulatoryDocument, DocumentVersion, Clause, Obligation, EngineeringTask, RepositoryScan, SourceCheck, CodeRepository, CodeChangeProposal, AuditEvent, GitHubInstallation, GitHubRepository, GitHubWebhookDelivery, GitHubPullRequest
from mitro.audit import record_event
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

class ObligationStatusIn(BaseModel):
    status: str = Field(min_length=2, max_length=40)
    actor: str = Field(min_length=2, max_length=160)
    note: str = Field(default="", max_length=4000)

class EngineeringTaskIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    assignee: str = Field(default="", max_length=160)
    due_date: str = Field(default="", max_length=20)

class EngineeringTaskUpdateIn(BaseModel):
    status: str = Field(min_length=2, max_length=32)
    actor: str = Field(min_length=2, max_length=160)
    blocker: str = Field(default="", max_length=4000)

OBLIGATION_STATUSES = {
    "drafted", "under_compliance_review", "approved_for_investigation",
    "engineering_investigation", "change_proposed", "testing_and_security_review",
    "awaiting_approval", "implemented_closed", "rejected", "not_applicable",
    "deferred", "blocked",
}

class RepositoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    path: str = Field(min_length=3, max_length=2000)

class DependencyAnalysisIn(BaseModel):
    package: str = Field(min_length=1, max_length=120)
    proposed_version: str = Field(min_length=1, max_length=80)
    release_notes: str = Field(default="", max_length=12000)
    repository_id: int = 0

class GitHubRepositorySelectionIn(BaseModel):
    repository_id: int
    selected: bool = True

class GitHubPullRequestIn(BaseModel):
    repository_id: int
    obligation_id: int
    actor: str = Field(min_length=2, max_length=160)
    reviewer_note: str = Field(default="", max_length=4000)
    base_branch: str = Field(default="", max_length=200)

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

_github_install_states: dict[str, float] = {}
_github_client_instance = None

def _github_client():
    global _github_client_instance
    from mitro.github_app import GitHubAppClient
    if _github_client_instance is None:
        _github_client_instance = GitHubAppClient()
    return _github_client_instance

def _github_installation(db: Session, record_id: int) -> GitHubInstallation:
    row = db.get(GitHubInstallation, record_id)
    if not row:
        raise HTTPException(404, "GitHub App installation not found")
    return row

@app.get("/api/github/status")
def github_status(db: Session = Depends(get_db)):
    from mitro.github_app import GitHubAppConfig, GitHubNotConfigured
    try:
        config = GitHubAppConfig.load()
        ready = True
    except GitHubNotConfigured:
        config, ready = None, False
    installations = db.scalars(select(GitHubInstallation).order_by(GitHubInstallation.id)).all()
    return {"configured": ready, "app_slug": config.slug if config else "",
            "pull_requests_enabled": bool(config and config.enable_pull_requests),
            "installations": [{"id": x.id, "installation_id": x.installation_id,
                "account": x.account_login, "account_type": x.account_type} for x in installations],
            "setup": "Configure GitHub App credentials and callback URL to enable connection." if not ready else "Ready to connect a GitHub App installation."}

@app.get("/api/github/connect")
def github_connect():
    from mitro.github_app import GitHubAppConfig, GitHubNotConfigured
    try:
        config = GitHubAppConfig.load()
    except GitHubNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    state = uuid.uuid4().hex
    _github_install_states[state] = __import__("time").time() + 600
    from urllib.parse import urlencode
    query = urlencode({"state": state})
    return RedirectResponse(f"https://github.com/apps/{config.slug}/installations/new?{query}", status_code=302)

@app.get("/api/github/callback")
def github_callback(installation_id: int, state: str, setup_action: str = "install",
                    db: Session = Depends(get_db)):
    from mitro.github_app import GitHubAPIError, GitHubNotConfigured
    expiry = _github_install_states.pop(state, 0)
    if expiry < __import__("time").time():
        raise HTTPException(400, "GitHub setup state is missing or expired. Start the connection again.")
    if setup_action not in {"install", "update"}:
        raise HTTPException(400, "GitHub installation was not completed")
    try:
        info = _github_client().app_get(f"/app/installations/{installation_id}")
    except GitHubNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(exc.status, f"Could not verify the GitHub installation: {exc}") from exc
    account = info.get("account") or {}
    row = db.scalar(select(GitHubInstallation).where(GitHubInstallation.installation_id == installation_id))
    if row is None:
        row = GitHubInstallation(installation_id=installation_id, account_login=account.get("login", "unknown"),
            account_type=account.get("type", ""), created_at=datetime.now(timezone.utc).isoformat())
        db.add(row)
    else:
        row.account_login = account.get("login", row.account_login)
        row.account_type = account.get("type", row.account_type)
    db.commit(); db.refresh(row)
    record_event(db, "github_app_connected", "github_installation", row.id,
        installation_id=installation_id, account=row.account_login, setup_action=setup_action)
    db.commit()
    return RedirectResponse("/workbench?view=code&github=connected", status_code=303)

@app.get("/api/github/installations/{installation_record_id}/repositories")
def github_available_repositories(installation_record_id: int, db: Session = Depends(get_db)):
    from mitro.github_app import GitHubAPIError, GitHubNotConfigured
    installation = _github_installation(db, installation_record_id)
    result = []
    try:
        client = _github_client()
        page = 1
        while page <= 50:
            response = client.get(installation.installation_id, "/installation/repositories",
                                  params={"per_page": 100, "page": page})
            batch = response.json().get("repositories", [])
            result.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    except (GitHubAPIError, GitHubNotConfigured) as exc:
        status = exc.status if isinstance(exc, GitHubAPIError) else 503
        raise HTTPException(status, str(exc)) from exc
    saved = {r.github_repo_id: r for r in db.scalars(select(GitHubRepository).where(
        GitHubRepository.installation_record_id == installation.id)).all()}
    return [{"github_id": repo["id"], "repository_id": saved[repo["id"]].id if repo["id"] in saved else None,
             "full_name": repo["full_name"],
             "private": bool(repo.get("private")), "default_branch": repo.get("default_branch", "main"),
             "selected": bool(saved.get(repo["id"]) and saved[repo["id"]].selected)} for repo in result]

@app.post("/api/github/installations/{installation_record_id}/repositories/select")
def select_github_repository(installation_record_id: int, body: GitHubRepositorySelectionIn,
                             db: Session = Depends(get_db)):
    from mitro.github_app import GitHubAPIError, GitHubNotConfigured
    installation = _github_installation(db, installation_record_id)
    try:
        response = _github_client().get(installation.installation_id,
            "/installation/repositories", params={"per_page": 100, "page": 1})
        all_repos = response.json().get("repositories", [])
        page = 2
        while len(all_repos) % 100 == 0 and len(all_repos) and page <= 50:
            batch = _github_client().get(installation.installation_id,
                "/installation/repositories", params={"per_page": 100, "page": page}).json().get("repositories", [])
            all_repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    except (GitHubAPIError, GitHubNotConfigured) as exc:
        status = exc.status if isinstance(exc, GitHubAPIError) else 503
        raise HTTPException(status, str(exc)) from exc
    remote = next((r for r in all_repos if r["id"] == body.repository_id), None)
    if not remote:
        raise HTTPException(404, "Repository is not accessible to this GitHub App installation")
    row = db.scalar(select(GitHubRepository).where(GitHubRepository.github_repo_id == body.repository_id))
    if row is None:
        row = GitHubRepository(installation_record_id=installation.id, github_repo_id=remote["id"],
            full_name=remote["full_name"], default_branch=remote.get("default_branch", "main"),
            private=bool(remote.get("private")), selected=body.selected)
        db.add(row)
    else:
        row.installation_record_id, row.full_name = installation.id, remote["full_name"]
        row.default_branch, row.private, row.selected = remote.get("default_branch", "main"), bool(remote.get("private")), body.selected
    db.commit(); db.refresh(row)
    record_event(db, "github_repository_selection_changed", "github_repository", row.id,
        full_name=row.full_name, selected=row.selected, branch=row.default_branch)
    db.commit()
    return {"id": row.id, "full_name": row.full_name, "selected": row.selected,
            "default_branch": row.default_branch, "message": "Repository selection saved."}

@app.get("/api/github/repositories/{repository_id}/branches")
def github_repository_branches(repository_id: int, db: Session = Depends(get_db)):
    from mitro.github_app import GitHubAPIError, GitHubNotConfigured
    repo = db.get(GitHubRepository, repository_id)
    if not repo or not repo.selected:
        raise HTTPException(404, "Selected GitHub repository not found")
    installation = _github_installation(db, repo.installation_record_id)
    owner, name = repo.full_name.split("/", 1)
    try:
        client = _github_client()
        rows, page = [], 1
        while page <= 50:
            batch = client.get(installation.installation_id,
                f"/repos/{owner}/{name}/branches", repo_ids=[repo.github_repo_id],
                params={"per_page": 100, "page": page}).json()
            rows.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    except (GitHubAPIError, GitHubNotConfigured) as exc:
        status = exc.status if isinstance(exc, GitHubAPIError) else 503
        raise HTTPException(status, str(exc)) from exc
    return [{"name": row["name"], "protected": bool(row.get("protected")),
             "default": row["name"] == repo.default_branch} for row in rows]

@app.post("/api/github/repositories/{repository_id}/scan")
def scan_github_repository(repository_id: int, branch: str, db: Session = Depends(get_db)):
    from mitro.github_app import GitHubAPIError, GitHubNotConfigured
    repo = db.get(GitHubRepository, repository_id)
    if not repo or not repo.selected:
        raise HTTPException(404, "Selected GitHub repository not found")
    if not branch or len(branch) > 200 or branch.startswith("-") or ".." in branch or "\\" in branch:
        raise HTTPException(422, "Choose a valid branch name")
    installation = _github_installation(db, repo.installation_record_id)
    owner, name = repo.full_name.split("/", 1)
    try:
        archive = _github_client().download_archive(installation.installation_id, repo.github_repo_id, owner, name, branch)
    except (GitHubAPIError, GitHubNotConfigured) as exc:
        status = exc.status if isinstance(exc, GitHubAPIError) else 503
        raise HTTPException(status, str(exc)) from exc
    if len(archive) > 100 * 1024 * 1024:
        raise HTTPException(413, "Repository archive exceeds the 100 MB scan limit")
    extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".sql", ".yaml", ".yml", ".json"}
    blocked_parts = {".git", ".venv", "venv", "node_modules", "__pycache__", ".next", "dist", "build", ".github"}
    with tempfile.TemporaryDirectory(prefix="mitro-github-scan-") as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        total, count = 0, 0
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                members = bundle.infolist()
                if len(members) > 10000:
                    raise HTTPException(413, "Repository archive contains too many entries")
                for member in members:
                    if member.is_dir():
                        continue
                    parts = Path(member.filename).parts
                    rel_parts = parts[1:]
                    rel = Path(*rel_parts) if rel_parts else Path()
                    if rel.is_absolute() or ".." in rel.parts or any(part.lower() in blocked_parts for part in rel.parts):
                        continue
                    if rel.suffix.lower() not in extensions or rel.name.lower() in {".env", "secrets.json"}:
                        continue
                    total += member.file_size
                    if total > 100 * 1024 * 1024:
                        raise HTTPException(413, "Repository source files exceed the 100 MB scan limit")
                    destination = root / rel
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(bundle.read(member))
                    count += 1
        except zipfile.BadZipFile as exc:
            raise HTTPException(502, "GitHub returned an invalid repository archive") from exc
        result = scan_repository(root)
    result["repository"] = repo.full_name
    result["branch"] = branch
    result["scan_mode"] = "read_only_github_archive"
    repo.last_scan_at = datetime.now(timezone.utc).isoformat()
    repo.last_scan_summary = result
    db.add(RepositoryScan(repository_path=f"github:{repo.full_name}", scanned_at=repo.last_scan_at,
        engine="Mitro read-only GitHub scan", summary={"branch": branch, "file_count": result["file_count"],
        "candidate_findings": result["candidate_findings"][:2000], "node_count": result["node_count"],
        "edge_count": result["edge_count"]}))
    record_event(db, "github_repository_scanned", "github_repository", repo.id,
        full_name=repo.full_name, branch=branch, file_count=result["file_count"],
        findings=len(result["candidate_findings"]))
    db.commit()
    return result

@app.get("/api/github/repositories/{repository_id}/scans")
def github_scan_history(repository_id: int, db: Session = Depends(get_db)):
    repo = db.get(GitHubRepository, repository_id)
    if not repo:
        raise HTTPException(404, "GitHub repository not found")
    rows = db.scalars(select(RepositoryScan).where(
        RepositoryScan.repository_path == f"github:{repo.full_name}").order_by(RepositoryScan.id.desc()).limit(30)).all()
    return [{"scanned_at": row.scanned_at, **row.summary} for row in rows]

@app.get("/api/github/obligations/{obligation_id}/impact")
def github_obligation_impact(obligation_id: int, repository_id: int, branch: str,
                             db: Session = Depends(get_db)):
    obligation = db.get(Obligation, obligation_id)
    if not obligation:
        raise HTTPException(404, "Obligation not found")
    approved_states = {"approved", "approved_for_investigation", "engineering_investigation",
        "change_proposed", "testing_and_security_review", "awaiting_approval", "implemented_closed"}
    if obligation.status not in approved_states:
        raise HTTPException(409, "Approve the obligation for investigation before mapping it to repository code")
    repo = db.get(GitHubRepository, repository_id)
    if not repo or not repo.selected:
        raise HTTPException(404, "Selected GitHub repository not found")
    snapshot = repo.last_scan_summary or {}
    if snapshot.get("branch") != branch:
        raise HTTPException(409, "Run a fresh read-only scan of the selected branch before mapping impact")
    if snapshot.get("stale"):
        raise HTTPException(409, "A repository push arrived after the last scan. Rescan before mapping impact")
    terms = {term.lower() for term in __import__("re").findall(r"[a-z][a-z0-9_]{3,}",
        obligation.statement + " " + obligation.quote)}
    stop = {"shall", "must", "will", "from", "under", "with", "that", "this", "where",
            "such", "their", "customer", "customers", "applicant", "application", "obligation",
            "regulatory", "direction", "lender", "records"}
    terms -= stop
    findings = []
    for finding in snapshot.get("candidate_findings", []):
        searchable = " ".join(str(finding.get(key, "")) for key in ("file", "snippet", "explanation")).lower()
        matches = sorted(term for term in terms if term in searchable)
        if matches:
            findings.append({**finding, "matched_terms": matches[:12],
                "classification": "candidate_for_human_review"})
    result = {"obligation_id": obligation.id, "obligation_key": obligation.key,
        "obligation_status": obligation.status, "repository": repo.full_name, "branch": branch,
        "scan_at": repo.last_scan_at, "candidate_code_locations": findings[:100],
        "candidate_count": len(findings), "human_review_required": True,
        "note": "Matches are leads for investigation. They do not establish a control gap or breach."}
    record_event(db, "github_obligation_impact_mapped", "obligation", obligation.id,
        repository=repo.full_name, branch=branch, candidate_count=len(findings))
    db.commit()
    return result

@app.post("/api/github/webhook")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    from mitro.github_app import GitHubAppConfig, GitHubNotConfigured, verify_webhook
    try:
        config = GitHubAppConfig.load()
    except GitHubNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    if not config.webhook_secret:
        raise HTTPException(503, "Configure MITRO_GITHUB_WEBHOOK_SECRET before enabling webhooks")
    body = await request.body()
    if len(body) > 2 * 1024 * 1024:
        raise HTTPException(413, "Webhook payload exceeds the 2 MB limit")
    if not verify_webhook(config.webhook_secret, body, request.headers.get("X-Hub-Signature-256", "")):
        raise HTTPException(401, "Webhook signature is invalid")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event = request.headers.get("X-GitHub-Event", "")
    if not delivery_id or not event:
        raise HTTPException(400, "Missing GitHub webhook delivery headers")
    if db.scalar(select(GitHubWebhookDelivery).where(GitHubWebhookDelivery.delivery_id == delivery_id)):
        return {"accepted": True, "duplicate": True}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Webhook payload must be valid JSON") from exc
    action = str(payload.get("action", ""))
    repo_name = str((payload.get("repository") or {}).get("full_name", ""))[:300]
    summary = {"ref": str(payload.get("ref", ""))[:240], "sender": str((payload.get("sender") or {}).get("login", ""))[:160]}
    delivery = GitHubWebhookDelivery(delivery_id=delivery_id, event=event, action=action,
        repository=repo_name, received_at=datetime.now(timezone.utc).isoformat(), processed=True, summary=summary)
    db.add(delivery)
    if event == "pull_request":
        pull_payload = payload.get("pull_request") or {}
        number = pull_payload.get("number")
        if number:
            github_repo = db.scalar(select(GitHubRepository).where(GitHubRepository.full_name == repo_name))
            pr = db.scalar(select(GitHubPullRequest).where(
                GitHubPullRequest.number == int(number),
                GitHubPullRequest.repository_id == github_repo.id)) if github_repo else None
            if pr:
                pr.state = "merged" if pull_payload.get("merged_at") else str(pull_payload.get("state", action))
    elif event == "push" and repo_name:
        tracked = db.scalar(select(GitHubRepository).where(GitHubRepository.full_name == repo_name))
        if tracked:
            tracked.last_scan_summary = {**(tracked.last_scan_summary or {}), "stale": True,
                "last_change_ref": summary["ref"], "last_change_at": datetime.now(timezone.utc).isoformat()}
    record_event(db, "github_webhook_received", "github_delivery", delivery_id,
        event=event, webhook_action=action, repository=repo_name, summary=summary)
    db.commit()
    return {"accepted": True, "duplicate": False, "event": event, "action": action}

@app.get("/api/audit")
def list_audit_events(limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 500))
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)).all()
    return [{"id": event.id, "occurred_at": event.occurred_at, "action": event.action,
             "entity_type": event.entity_type, "entity_id": event.entity_id, "details": event.details}
            for event in events]

@app.post("/api/dependencies/analyze")
def dependency_impact_analysis(body: DependencyAnalysisIn, db: Session = Depends(get_db)):
    from mitro.dependencies import analyze_dependency_update
    path = _repository_path("targets/lendwise", body.repository_id, db)
    try:
        result = analyze_dependency_update(path, body.package, body.proposed_version, body.release_notes)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    record_event(db, "dependency_update_analyzed", "repository", body.repository_id,
                 package=result["package"], proposed_version=result["proposed_version"],
                 affected_files=len(result["code_uses"]))
    db.commit()
    return result

@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.scalars(select(RegulatoryDocument).order_by(RegulatoryDocument.id)).all()
    return [{"id": d.id, "regulator": d.regulator, "identifier": d.identifier, "title": d.title,
             "source_url": d.source_url, "versions": [{"id": v.id, "date": v.version_date,
             "file": v.source_filename, "hash": v.sha256, "extraction": v.extraction_method,
             "page_count": v.provenance.get("page_count", 0),
             "extraction_warning": v.provenance.get("extraction_warning", ""),
             "page_status": v.provenance.get("page_status", []),
             "structured_extraction": v.provenance.get("structured_extraction", "page_text_only"),
             "structured_warning": v.provenance.get("structured_warning", ""),
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
    record_event(db, "repository_registered", "repository", repo.id, name=repo.name,
                 source_kind="local_path")
    db.commit()
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
        result = ingest_file(db, target, {"regulator": regulator, "identifier": identifier, "title": title,
             "version_date": version_date, "publication_date": publication_date, "source_url": source_url,
             "source_kind": "uploaded"})
        record_event(db, "document_uploaded", "document", result["document_id"], identifier=identifier,
                     version_id=result["version_id"], sha256=result.get("sha256", ""))
        db.commit()
        return result
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
        result = ingest_file(db, target, {"regulator": regulator, "identifier": identifier, "title": title,
             "version_date": version_date, "publication_date": publication_date, "source_url": url,
             "source_kind": "fetched_official_source"})
        record_event(db, "official_source_ingested", "document", result["document_id"],
                     identifier=identifier, version_id=result["version_id"],
                     sha256=result.get("sha256", ""))
        db.commit()
        return result
    except Exception as exc:
        raise HTTPException(400, f"Fetched file could not be ingested: {exc}") from exc
@app.post("/api/bootstrap")
def bootstrap_sources(db: Session = Depends(get_db)):
    try:
        ingested = bootstrap(db)
        record_event(db, "corpus_bootstrapped", "source_corpus", "included", documents=len(ingested))
        db.commit()
        return {"ingested": ingested}
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
    record_event(db, "demo_obligation_created", "obligation", obligation.id,
                 key=obligation.key, clause_id=obligation.clause_id)
    db.commit()
    return {"id": obligation.id, "key": obligation.key, "status": obligation.status,
            "citation": clause.citation,
            "message": "Sample created as proposed. Review and approve it before mapping it to code."}

@app.get("/api/versions/{version_id}/clauses")
def list_clauses(version_id: int, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version: raise HTTPException(404, "Version not found")
    clauses = db.scalars(select(Clause).where(Clause.version_id == version_id).order_by(Clause.ordinal)).all()
    return [{"id": c.id, "citation": c.citation, "text": c.text,
             "page_number": c.page_number, "coordinates": c.coordinates or []}
            for c in clauses]

@app.get("/api/versions/{version_id}/extraction")
def structured_extraction(version_id: int, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version:
        raise HTTPException(404, "Document version not found")
    artifact = Path(version.provenance.get("structured_artifact", "")).resolve()
    extraction_root = (ROOT / "data" / "extractions").resolve()
    if not artifact.is_relative_to(extraction_root) or not artifact.is_file():
        raise HTTPException(404, "Structured extraction artifact is unavailable")
    try:
        return json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Stored extraction artifact could not be read") from exc

@app.get("/api/versions/{version_id}/pdf")
def original_pdf(version_id: int, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version:
        raise HTTPException(404, "Document version not found")
    path = Path(version.stored_path).resolve()
    allowed_roots = [(DATA_DIR / "raw").resolve(), (ROOT / "sources").resolve()]
    if path.suffix.lower() != ".pdf" or not path.is_file() or not any(path.is_relative_to(root) for root in allowed_roots):
        raise HTTPException(404, "Original PDF is unavailable")
    return FileResponse(path, media_type="application/pdf", filename=version.source_filename,
                        content_disposition_type="inline")

@app.get("/api/redline")
def get_redline(old_version_id: int, new_version_id: int, db: Session = Depends(get_db)):
    try: return redline(db, old_version_id, new_version_id)
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc

@app.get("/api/versions/{old_version_id}/impact/{new_version_id}")
def regulatory_change_impact(old_version_id: int, new_version_id: int, repository_id: int = 0,
                              db: Session = Depends(get_db)):
    old, new = db.get(DocumentVersion, old_version_id), db.get(DocumentVersion, new_version_id)
    if not old or not new:
        raise HTTPException(404, "Both regulatory versions must exist")
    if old.document_id != new.document_id:
        raise HTTPException(422, "Choose two versions of the same regulatory document")
    old_clauses = db.scalars(select(Clause).where(Clause.version_id == old.id)).all()
    new_clauses = db.scalars(select(Clause).where(Clause.version_id == new.id)).all()
    old_by = {c.citation: c for c in old_clauses}; new_by = {c.citation: c for c in new_clauses}
    path = _repository_path("targets/lendwise", repository_id, db)
    changes = []
    for citation in sorted(set(old_by) | set(new_by)):
        before, after = old_by.get(citation), new_by.get(citation)
        if before and after and before.text.strip() == after.text.strip():
            continue
        linked = db.scalars(select(Obligation).where(Obligation.clause_id == before.id)).all() if before else []
        obligations = []
        for obligation in linked:
            candidates = impact_candidates(path, obligation.statement, obligation.quote, citation) if obligation.status in {"approved", "approved_for_investigation", "engineering_investigation", "change_proposed", "testing_and_security_review", "awaiting_approval", "implemented_closed"} else []
            obligations.append({"id": obligation.id, "key": obligation.key, "status": obligation.status,
                                "review_required": True, "candidate_code_locations": candidates})
        changes.append({"citation": citation, "change_type": "added" if not before else "removed" if not after else "amended",
                        "old_text": before.text if before else "", "new_text": after.text if after else "",
                        "obligations": obligations, "human_review_required": True})
    result = {"document": old.document.identifier, "old_version": {"id": old.id, "date": old.version_date, "sha256": old.sha256},
              "new_version": {"id": new.id, "date": new.version_date, "sha256": new.sha256},
              "changed_clause_count": len(changes), "changes": changes,
              "limitations": ["Clause citations are matched heuristically; numbering changes can split or merge clauses.",
                              "Code locations are candidates only. A qualified reviewer must confirm applicability and impact."]}
    record_event(db, "regulatory_impact_compared", "document", old.document.identifier,
                 old_version_id=old.id, new_version_id=new.id, changed_clauses=len(changes))
    db.commit()
    return result

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
        result = await draft_for_version(db, version_id)
        record_event(db, "ai_obligations_drafted", "document_version", version_id,
                     provider=result.get("provider", ""), model=result.get("model", ""),
                     proposed_count=len(result.get("proposed", [])),
                     rejected_count=len(result.get("rejected", [])))
        db.commit()
        return result
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
    record_event(db, "obligation_proposed", "obligation", ob.id, key=ob.key, clause_id=clause.id)
    db.commit()
    return {"id": ob.id, "key": ob.key, "status": ob.status}

@app.get("/api/obligations")
def list_obligations(db: Session = Depends(get_db)):
    obs = db.scalars(select(Obligation).order_by(Obligation.id)).all()
    return [{"id": o.id, "key": o.key, "clause_id": o.clause_id, "quote": o.quote,
             "statement": o.statement, "shape": o.engineering_shape, "status": o.status,
             "approved_by": o.approved_by, "history": _obligation_history(db, o.id)} for o in obs]

def _obligation_history(db: Session, obligation_id: int):
    events = db.scalars(select(AuditEvent).where(
        AuditEvent.entity_type == "obligation", AuditEvent.entity_id == str(obligation_id)
    ).order_by(AuditEvent.id)).all()
    return [{"at": event.occurred_at, "action": event.action, "details": event.details} for event in events]

@app.get("/api/obligations/{obligation_id}/history")
def obligation_history(obligation_id: int, db: Session = Depends(get_db)):
    if not db.get(Obligation, obligation_id):
        raise HTTPException(404, "Obligation not found")
    return _obligation_history(db, obligation_id)

@app.get("/api/obligations/{obligation_id}/tasks")
def list_engineering_tasks(obligation_id: int, db: Session = Depends(get_db)):
    if not db.get(Obligation, obligation_id):
        raise HTTPException(404, "Obligation not found")
    rows = db.scalars(select(EngineeringTask).where(
        EngineeringTask.obligation_id == obligation_id).order_by(EngineeringTask.id)).all()
    return [{"id": row.id, "title": row.title, "assignee": row.assignee,
             "due_date": row.due_date, "status": row.status, "blocker": row.blocker}
            for row in rows]

@app.post("/api/obligations/{obligation_id}/tasks")
def create_engineering_task(obligation_id: int, body: EngineeringTaskIn, db: Session = Depends(get_db)):
    if not db.get(Obligation, obligation_id):
        raise HTTPException(404, "Obligation not found")
    task = EngineeringTask(obligation_id=obligation_id, title=body.title.strip(),
        assignee=body.assignee.strip(), due_date=body.due_date,
        created_at=datetime.now(timezone.utc).isoformat())
    db.add(task); db.commit(); db.refresh(task)
    record_event(db, "engineering_task_created", "obligation", obligation_id,
        task_id=task.id, title=task.title, assignee=task.assignee, due_date=task.due_date)
    db.commit()
    return {"id": task.id, "title": task.title, "assignee": task.assignee,
            "due_date": task.due_date, "status": task.status}

@app.patch("/api/tasks/{task_id}")
def update_engineering_task(task_id: int, body: EngineeringTaskUpdateIn, db: Session = Depends(get_db)):
    task = db.get(EngineeringTask, task_id)
    if not task:
        raise HTTPException(404, "Engineering task not found")
    if body.status not in {"open", "in_progress", "blocked", "done", "cancelled"}:
        raise HTTPException(422, "Choose open, in_progress, blocked, done, or cancelled")
    previous = task.status
    task.status, task.blocker = body.status, body.blocker
    db.commit()
    record_event(db, "engineering_task_updated", "obligation", task.obligation_id,
        task_id=task.id, previous_status=previous, status=task.status,
        blocker=task.blocker, actor=body.actor)
    db.commit()
    return {"id": task.id, "status": task.status, "previous_status": previous}

@app.post("/api/obligations/{obligation_id}/status")
def update_obligation_status(obligation_id: int, body: ObligationStatusIn, db: Session = Depends(get_db)):
    ob = db.get(Obligation, obligation_id)
    if not ob:
        raise HTTPException(404, "Obligation not found")
    if body.status not in OBLIGATION_STATUSES:
        raise HTTPException(422, "Choose a supported obligation lifecycle status")
    previous = ob.status
    ob.status = body.status
    if body.status == "approved_for_investigation":
        ob.approved_by = body.actor
        ob.approved_at = datetime.now(timezone.utc).isoformat()
    if body.note:
        ob.reviewer_note = body.note
    db.commit()
    record_event(db, "obligation_status_changed", "obligation", ob.id,
                 previous_status=previous, status=body.status, actor=body.actor,
                 note=body.note, clause_id=ob.clause_id)
    db.commit()
    return {"id": ob.id, "status": ob.status, "previous_status": previous}

@app.post("/api/obligations/{obligation_id}/approve")
def approve_obligation(obligation_id: int, body: ApprovalIn, db: Session = Depends(get_db)):
    ob = db.get(Obligation, obligation_id)
    if not ob: raise HTTPException(404, "Obligation not found")
    ob.status = "approved"; ob.approved_by = body.approver
    ob.approved_at = datetime.now(timezone.utc).isoformat(); ob.reviewer_note = body.reviewer_note
    db.commit()
    record_event(db, "obligation_approved", "obligation", ob.id, reviewer=body.approver,
                 clause_id=ob.clause_id)
    db.commit()
    return {"id": ob.id, "status": ob.status, "approved_by": ob.approved_by}

def _proposal_json(proposal: CodeChangeProposal, db: Session | None = None) -> dict:
    clause = proposal.clause_id
    from mitro.phase3.safety import evaluate_patch_safety
    safety = evaluate_patch_safety(proposal.scenario, proposal.edits)
    linked = []
    if db is not None:
        linked = db.scalars(select(Obligation).where(Obligation.clause_id == proposal.clause_id)).all()
    return {"id": proposal.id, "clause_id": clause, "scenario": proposal.scenario,
            "source_citation": proposal.source_citation or "", "source_identifier": proposal.source_identifier or "",
            "source_url": proposal.source_url or "", "source_sha256": proposal.source_sha256 or "",
            "title": proposal.title, "quote": proposal.quote, "statement": proposal.statement,
            "expected_behavior": proposal.expected_behavior, "rationale": proposal.rationale,
            "diff": proposal.diff, "test_status": proposal.test_status,
            "safety_review": safety,
            "evidence_grounding": {"source_identifier": proposal.source_identifier,
                "source_citation": proposal.source_citation, "source_sha256": proposal.source_sha256,
                "verbatim_quote_present": bool(proposal.quote),
                "code_files": [e.get("file", "") for e in proposal.edits],
                "linked_obligations": [{"id": o.id, "key": o.key, "status": o.status} for o in linked],
        "approved_obligation_present": any(o.status in {"approved", "approved_for_investigation", "engineering_investigation", "change_proposed", "testing_and_security_review", "awaiting_approval", "implemented_closed"} for o in linked),
                "human_review_required": True},
            "test_output": proposal.test_output, "copy_ready": bool(proposal.bundle_path),
            "download_url": f"/api/phase3/proposals/{proposal.id}/download" if proposal.bundle_path else "",
        "created_at": proposal.created_at}

@app.post("/api/github/proposals/{proposal_id}/pull-request")
def create_github_pull_request(proposal_id: int, body: GitHubPullRequestIn,
                               db: Session = Depends(get_db)):
    from urllib.parse import quote as urlquote
    from mitro.github_app import GitHubAPIError, GitHubNotConfigured
    from mitro.phase3.safety import evaluate_patch_safety, SECRET_RE
    proposal = db.get(CodeChangeProposal, proposal_id)
    repo = db.get(GitHubRepository, body.repository_id)
    if not proposal:
        raise HTTPException(404, "Patch proposal not found")
    if not repo or not repo.selected:
        raise HTTPException(404, "Choose a repository registered to this GitHub App installation")
    if not os.getenv("MITRO_GITHUB_ENABLE_PULL_REQUESTS", "false").lower() == "true":
        raise HTTPException(403, "Pull-request creation is disabled. Set MITRO_GITHUB_ENABLE_PULL_REQUESTS=true only after granting the App write permissions.")
    obligation = db.get(Obligation, body.obligation_id)
    if not obligation or obligation.clause_id != proposal.clause_id:
        raise HTTPException(422, "The approved obligation must cite the clause used by this patch proposal")
    clause = db.get(Clause, proposal.clause_id)
    if not clause or proposal.quote != clause.text or obligation.quote not in clause.text:
        raise HTTPException(422, "The patch and obligation must retain an exact quote from the extracted source clause")
    if obligation.status not in {"approved", "approved_for_investigation", "engineering_investigation", "change_proposed", "testing_and_security_review", "awaiting_approval"}:
        raise HTTPException(409, "Move the linked obligation to an approved investigation state before requesting a pull request")
    if proposal.test_status != "passed":
        raise HTTPException(409, "Run and pass the proposal's scoped regression check before requesting a pull request")
    safety = evaluate_patch_safety(proposal.scenario, proposal.edits)
    if not safety["allowed"]:
        raise HTTPException(422, "Safe Patch Guard blocked the proposal: " + "; ".join(safety["reasons"]))
    installation = _github_installation(db, repo.installation_record_id)
    owner, name = repo.full_name.split("/", 1)
    api_repo = f"/repos/{owner}/{name}"
    try:
        client = _github_client()
        branches = client.get(installation.installation_id, f"{api_repo}/branches",
            repo_ids=[repo.github_repo_id], params={"per_page": 100}).json()
        base_branch = body.base_branch or repo.default_branch
        if not any(branch.get("name") == base_branch for branch in branches):
            raise HTTPException(422, "The selected base branch was not returned by GitHub for this repository")
        last_scan = db.scalar(select(RepositoryScan).where(
            RepositoryScan.repository_path == f"github:{repo.full_name}").order_by(RepositoryScan.id.desc()))
        if not last_scan or last_scan.summary.get("branch") != base_branch:
            raise HTTPException(409, "Run a read-only scan of this repository branch before requesting a pull request")
        if repo.last_scan_summary.get("stale"):
            raise HTTPException(409, "A repository push arrived after the last scan. Rescan before requesting a pull request")
        ref = client.get(installation.installation_id,
            f"{api_repo}/git/ref/heads/{urlquote(base_branch, safe='/')}", repo_ids=[repo.github_repo_id]).json()
        base_sha = ref["object"]["sha"]
        base_commit = client.get(installation.installation_id,
            f"{api_repo}/git/commits/{base_sha}", repo_ids=[repo.github_repo_id]).json()
        changes = []
        for edit in proposal.edits:
            file_path = edit["file"]
            encoded_path = urlquote(file_path, safe="/")
            content = client.get(installation.installation_id,
                f"{api_repo}/contents/{encoded_path}", repo_ids=[repo.github_repo_id],
                params={"ref": base_branch}).json()
            original = client.decode_content(content).decode("utf-8")
            before, after = str(edit["before"]), str(edit["after"])
            if not before or original.count(before) != 1:
                raise HTTPException(409, f"File {file_path} no longer matches the reviewed patch context")
            updated = original.replace(before, after, 1)
            if SECRET_RE.search(updated):
                raise HTTPException(422, f"Secret-like content detected in {file_path}; pull request blocked")
            blob = client.post(installation.installation_id, f"{api_repo}/git/blobs",
                repo_ids=[repo.github_repo_id], permissions={"contents": "write"},
                json={"content": base64.b64encode(updated.encode()).decode(), "encoding": "base64"}).json()
            changes.append({"path": file_path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = client.post(installation.installation_id, f"{api_repo}/git/trees",
            repo_ids=[repo.github_repo_id], permissions={"contents": "write"},
            json={"base_tree": base_commit["tree"]["sha"], "tree": changes}).json()
        branch = f"codex/mitro-obligation-{obligation.id}-{uuid.uuid4().hex[:8]}"
        commit = client.post(installation.installation_id, f"{api_repo}/git/commits",
            repo_ids=[repo.github_repo_id], permissions={"contents": "write"},
            json={"message": f"Mitro proposal: {proposal.title} ({obligation.key})",
                  "tree": tree["sha"], "parents": [base_sha]}).json()
        client.post(installation.installation_id, f"{api_repo}/git/refs",
            repo_ids=[repo.github_repo_id], permissions={"contents": "write"},
            json={"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        source_link = proposal.source_url or "Source URL not recorded"
        affected = "\n".join(f"- `{edit['file']}`" for edit in proposal.edits)
        quote_text = "\n".join("> " + line.replace("<", "&lt;").replace(">", "&gt;") for line in proposal.quote.splitlines())
        pr_body = (f"## Regulatory source\n{proposal.source_identifier}, clause {proposal.source_citation} ([source]({source_link}))\n\n"
            f"## Approved obligation\n**{obligation.key}** — {obligation.statement}\n\n"
            f"## Source excerpt\n{quote_text}\n\n## Affected files\n{affected}\n\n"
            f"## Proposed change\n{proposal.rationale}\n\n## Checks\n"
            f"- Safe Patch Guard: passed ({safety['changed_lines']} changed lines; {len(safety['files'])} file(s))\n"
            f"- Scoped Lendwise demonstration test: passed\n"
            f"- Target repository test suite: not run by Mitro\n\n"
            f"Requested by {body.actor}. This proposal requires developer review; Mitro will not merge it.")
        pr_data = client.post(installation.installation_id, f"{api_repo}/pulls",
            repo_ids=[repo.github_repo_id], permissions={"pull_requests": "write"},
            json={"title": f"[Mitro] {proposal.title}", "head": branch,
                  "base": base_branch, "body": pr_body, "draft": True}).json()
    except HTTPException:
        raise
    except (GitHubAPIError, GitHubNotConfigured) as exc:
        status = exc.status if isinstance(exc, GitHubAPIError) else 503
        raise HTTPException(status, str(exc)) from exc
    record = GitHubPullRequest(proposal_id=proposal.id, repository_id=repo.id,
        number=pr_data["number"], url=pr_data["html_url"], head_branch=branch,
        state=pr_data.get("state", "open"), created_at=datetime.now(timezone.utc).isoformat())
    db.add(record)
    record_event(db, "github_pull_request_created", "patch", proposal.id,
        repository=repo.full_name, pull_request_number=record.number,
        pull_request_url=record.url, head_branch=branch, base_branch=base_branch,
        actor=body.actor, reviewer_note=body.reviewer_note,
        target_repo_tests="not_run")
    db.commit(); db.refresh(record)
    return {"id": record.id, "number": record.number, "url": record.url,
        "head_branch": record.head_branch, "state": record.state,
        "target_repo_tests": "not_run", "safe_patch_guard": safety}

@app.get("/api/github/proposals/{proposal_id}/pull-requests")
def list_github_pull_requests(proposal_id: int, db: Session = Depends(get_db)):
    if not db.get(CodeChangeProposal, proposal_id):
        raise HTTPException(404, "Patch proposal not found")
    rows = db.scalars(select(GitHubPullRequest).where(
        GitHubPullRequest.proposal_id == proposal_id).order_by(GitHubPullRequest.id.desc())).all()
    return [{"id": row.id, "number": row.number, "url": row.url,
             "head_branch": row.head_branch, "state": row.state, "created_at": row.created_at}
            for row in rows]

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
    record_event(db, "patch_proposed", "patch", proposal.id, scenario=proposal.scenario,
                 clause_id=clause.id, source_sha256=proposal.source_sha256)
    db.commit()
    return {**_proposal_json(proposal, db), "method": draft["method"], "limitations": draft["limitations"],
            "message": "Draft only. Review the clause, interpretation, and diff before building the separate copy."}

@app.get("/api/phase3/proposals/{proposal_id}")
def get_code_change_proposal(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(CodeChangeProposal, proposal_id)
    if not proposal:
        raise HTTPException(404, "Code change proposal not found")
    return _proposal_json(proposal, db)

@app.post("/api/phase3/proposals/{proposal_id}/build")
def build_proposed_copy(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(CodeChangeProposal, proposal_id)
    if not proposal:
        raise HTTPException(404, "Code change proposal not found")
    from mitro.phase3.safety import evaluate_patch_safety
    from mitro.security.untrusted import inspect_untrusted_text
    guard = evaluate_patch_safety(proposal.scenario, proposal.edits)
    untrusted = inspect_untrusted_text(proposal.quote)
    if not guard["allowed"] or untrusted["flagged"]:
        reasons = guard["reasons"] + (["Instruction-like source text detected"] if untrusted["flagged"] else [])
        record_event(db, "patch_blocked_by_guard", "patch", proposal.id,
                     scenario=proposal.scenario, reasons=reasons)
        db.commit()
        raise HTTPException(409, "Safe Patch Guard blocked this build: " + "; ".join(reasons))
    try:
        result = build_and_verify(proposal, proposal.id)
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        raise HTTPException(409, str(exc)) from exc
    proposal.test_status = result["test_status"]
    proposal.test_output = result["test_output"]
    proposal.copy_path = result["copy_path"]
    proposal.bundle_path = result.get("bundle_path", proposal.bundle_path)
    db.commit()
    record_event(db, "patch_built_and_tested", "patch", proposal.id,
                 scenario=proposal.scenario, test_status=proposal.test_status,
                 source_sha256=proposal.source_sha256)
    db.commit()
    return {**_proposal_json(proposal, db), "test_output": result["test_output"],
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
    record_event(db, "repository_scanned", "repository_scan", scan.id,
                 repository=str(path), candidate_count=len(summary.get("candidate_findings", [])))
    db.commit()
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

@app.get("/workbench", include_in_schema=False)
def workbench():
    return FileResponse(ROOT / "web" / "index.html")




