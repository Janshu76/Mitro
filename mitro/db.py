from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

class RegulatoryDocument(Base):
    __tablename__ = "regulatory_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regulator: Mapped[str] = mapped_column(String(40), index=True)
    identifier: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(500))
    document_type: Mapped[str] = mapped_column(String(40), default="direction")
    source_url: Mapped[str] = mapped_column(Text, default="")
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_date", "sha256", name="uq_doc_version_hash"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("regulatory_documents.id"), index=True)
    version_date: Mapped[str] = mapped_column(String(20), index=True)
    publication_date: Mapped[str] = mapped_column(String(20), default="")
    source_filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    stored_path: Mapped[str] = mapped_column(Text)
    extracted_text: Mapped[str] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String(40))
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    document: Mapped[RegulatoryDocument] = relationship(back_populates="versions")
    clauses: Mapped[list["Clause"]] = relationship(back_populates="version", cascade="all, delete-orphan")

class Clause(Base):
    __tablename__ = "clauses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("document_versions.id"), index=True)
    citation: Mapped[str] = mapped_column(String(120), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coordinates: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[DocumentVersion] = relationship(back_populates="clauses")

class Obligation(Base):
    __tablename__ = "obligations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clause_id: Mapped[int] = mapped_column(ForeignKey("clauses.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    quote: Mapped[str] = mapped_column(Text)
    statement: Mapped[str] = mapped_column(Text)
    engineering_shape: Mapped[str] = mapped_column(String(30), default="code")
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)
    approved_by: Mapped[str] = mapped_column(String(160), default="")
    approved_at: Mapped[str] = mapped_column(String(40), default="")
    reviewer_note: Mapped[str] = mapped_column(Text, default="")

class EngineeringTask(Base):
    __tablename__ = "engineering_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    obligation_id: Mapped[int] = mapped_column(ForeignKey("obligations.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    assignee: Mapped[str] = mapped_column(String(160), default="")
    due_date: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    blocker: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(40))

class RepositoryScan(Base):
    __tablename__ = "repository_scans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_path: Mapped[str] = mapped_column(Text)
    scanned_at: Mapped[str] = mapped_column(String(40))
    engine: Mapped[str] = mapped_column(String(80))
    summary: Mapped[dict] = mapped_column(JSON, default=dict)

class SourceCheck(Base):
    __tablename__ = "source_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(180), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[str] = mapped_column(String(40), index=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id"), nullable=True)
    etag: Mapped[str] = mapped_column(Text, default="")
    last_modified: Mapped[str] = mapped_column(String(160), default="")
    detail: Mapped[str] = mapped_column(Text, default="")

class CodeRepository(Base):
    __tablename__ = "code_repositories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    root_path: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(40), default="local_path")
    created_at: Mapped[str] = mapped_column(String(40))

class GitHubInstallation(Base):
    __tablename__ = "github_installations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    installation_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    account_login: Mapped[str] = mapped_column(String(200))
    account_type: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[str] = mapped_column(String(40))

class GitHubRepository(Base):
    __tablename__ = "github_repositories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    installation_record_id: Mapped[int] = mapped_column(ForeignKey("github_installations.id"), index=True)
    github_repo_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(300), index=True)
    default_branch: Mapped[str] = mapped_column(String(200), default="main")
    private: Mapped[bool] = mapped_column(default=False)
    selected: Mapped[bool] = mapped_column(default=False, index=True)
    last_scan_at: Mapped[str] = mapped_column(String(40), default="")
    last_scan_summary: Mapped[dict] = mapped_column(JSON, default=dict)

class GitHubWebhookDelivery(Base):
    __tablename__ = "github_webhook_deliveries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    event: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80), default="")
    repository: Mapped[str] = mapped_column(String(300), default="")
    received_at: Mapped[str] = mapped_column(String(40))
    processed: Mapped[bool] = mapped_column(default=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)

class GitHubPullRequest(Base):
    __tablename__ = "github_pull_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("code_change_proposals.id"), index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("github_repositories.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(Text)
    head_branch: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(40), default="open")
    created_at: Mapped[str] = mapped_column(String(40))

class CodeChangeProposal(Base):
    __tablename__ = "code_change_proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clause_id: Mapped[int] = mapped_column(ForeignKey("clauses.id"), index=True)
    source_citation: Mapped[str] = mapped_column(String(120), default="")
    source_identifier: Mapped[str] = mapped_column(String(160), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_sha256: Mapped[str] = mapped_column(String(64), default="")
    scenario: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    quote: Mapped[str] = mapped_column(Text)
    statement: Mapped[str] = mapped_column(Text)
    expected_behavior: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    edits: Mapped[list] = mapped_column(JSON, default=list)
    diff: Mapped[str] = mapped_column(Text)
    test_source: Mapped[str] = mapped_column(Text)
    test_status: Mapped[str] = mapped_column(String(32), default="not_run", index=True)
    test_output: Mapped[str] = mapped_column(Text, default="")
    copy_path: Mapped[str] = mapped_column(Text, default="")
    bundle_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(40), index=True)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[str] = mapped_column(String(40), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(160), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
