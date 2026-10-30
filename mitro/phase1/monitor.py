"""On-demand, allow-listed checks of the official-source catalog."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from mitro.db import RegulatoryDocument, DocumentVersion, SourceCheck
from mitro.database import ROOT, DATA_DIR
from mitro.phase1.ingest import ingest_file

ALLOWED_HOSTS = {"rbi.org.in", "www.rbi.org.in", "website.rbi.org.in", "meity.gov.in", "www.meity.gov.in", "egazette.gov.in", "www.egazette.gov.in"}
MAX_BYTES = 25 * 1024 * 1024

def _safe_url(url: str) -> bool:
    p = urlparse(url)
    return p.scheme == "https" and (p.hostname or "").lower() in ALLOWED_HOSTS and p.port in (None, 443) and not p.username and not p.password

async def _get_official(client: httpx.AsyncClient, url: str) -> tuple[httpx.Response, str]:
    current = url
    for _ in range(4):
        if not _safe_url(current):
            raise ValueError("Redirect left the official-source allowlist")
        response = await client.get(current, follow_redirects=False)
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                raise ValueError("Official source returned a redirect without a location")
            current = urljoin(current, location)
            continue
        return response, current
    raise ValueError("Official source exceeded the redirect limit")

def _suffix(response: httpx.Response, url: str) -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in {".pdf", ".txt", ".md", ".xml", ".html"}:
        return ext
    typ = response.headers.get("content-type", "").lower()
    return ".pdf" if "pdf" in typ else ".html" if "html" in typ else ".xml" if "xml" in typ else ".txt"

async def refresh_official_sources(db: Session, catalog_path: Path | None = None) -> dict:
    """Fetch each configured official URL; retain every response and check result."""
    catalog_path = catalog_path or ROOT / "sources" / "catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8-sig")) or {}
    checked = []
    async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "Mitro-Regulatory-Review/0.1"}) as client:
        for item in catalog.get("sources", []):
            source_id = str(item.get("id", "")).strip()
            url = str(item.get("official_url", "")).strip()
            if not source_id or not _safe_url(url):
                continue
            record = {"source_id": source_id, "source_url": url, "checked_at": datetime.now(timezone.utc).isoformat(),
                      "outcome": "error", "http_status": None, "sha256": "", "version_id": None,
                      "etag": "", "last_modified": "", "detail": ""}
            try:
                response, final_url = await _get_official(client, url)
                record["http_status"] = response.status_code
                if response.status_code >= 400:
                    raise ValueError(f"Source returned HTTP {response.status_code}")
                body = response.content
                if len(body) > MAX_BYTES:
                    raise ValueError("Source exceeds 25 MB")
                digest = hashlib.sha256(body).hexdigest()
                record["sha256"] = digest
                record["etag"] = response.headers.get("etag", "")[:500]
                record["last_modified"] = response.headers.get("last-modified", "")[:160]
                identifier = str(item.get("identifier") or source_id)
                document = db.scalar(select(RegulatoryDocument).where(
                    RegulatoryDocument.regulator == item.get("regulator", "RBI"),
                    RegulatoryDocument.identifier == identifier))
                existing = db.scalar(select(DocumentVersion).where(
                    DocumentVersion.document_id == document.id if document else False,
                    DocumentVersion.sha256 == digest)) if document else None
                if existing:
                    record["outcome"] = "unchanged"
                    record["version_id"] = existing.id
                    record["detail"] = "Content hash matches an ingested version."
                else:
                    suffix = _suffix(response, final_url)
                    filename = re.sub(r"[^A-Za-z0-9._-]+", "-", source_id)[:100] + suffix
                    path = DATA_DIR / "raw" / (uuid.uuid4().hex[:12] + "-" + filename)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                    vdate = str(item.get("publication_date") or datetime.now(timezone.utc).date().isoformat())
                    result = ingest_file(db, path, {"regulator": item.get("regulator", "RBI"),
                        "identifier": identifier, "title": item.get("title", source_id),
                        "document_type": item.get("document_type", "direction"),
                        "version_date": vdate, "publication_date": item.get("publication_date", ""),
                        "source_url": final_url, "source_kind": "official_source_monitor"})
                    record["outcome"] = "new_version"
                    record["version_id"] = result["version_id"]
                    record["detail"] = "New response stored with its source URL and content hash. Review the extracted text."
            except Exception as exc:
                record["detail"] = str(exc)[:500]
            db.add(SourceCheck(**record))
            db.commit()
            checked.append({k: record[k] for k in ("source_id", "source_url", "checked_at", "outcome", "http_status", "sha256", "version_id", "detail")})
    return {"checked": checked, "count": len(checked),
            "note": "Checks run only when requested. New versions are retained; review provenance and clause extraction before relying on them."}
