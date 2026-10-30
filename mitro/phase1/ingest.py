import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from mitro.db import RegulatoryDocument, DocumentVersion, Clause
from mitro.phase1.parser import extract_text, split_clauses, sha256_file

ROOT = Path(__file__).resolve().parents[2]

def ingest_file(db: Session, path: Path, metadata: dict) -> dict:
    path = path.resolve()
    text, method = extract_text(path)
    digest = sha256_file(path)
    identifier = metadata.get("identifier") or path.stem
    regulator = metadata.get("regulator", "RBI")
    doc = db.scalar(select(RegulatoryDocument).where(
        RegulatoryDocument.regulator == regulator, RegulatoryDocument.identifier == identifier))
    if not doc:
        doc = RegulatoryDocument(regulator=regulator, identifier=identifier,
            title=metadata.get("title", path.stem), document_type=metadata.get("document_type", "direction"),
            source_url=metadata.get("source_url", ""))
        db.add(doc)
        db.flush()
    dupe = db.scalar(select(DocumentVersion).where(
        DocumentVersion.document_id == doc.id,
        DocumentVersion.version_date == metadata.get("version_date", "unknown"),
        DocumentVersion.sha256 == digest))
    if dupe:
        return {"document_id": doc.id, "version_id": dupe.id, "duplicate": True, "clause_count": len(dupe.clauses)}
    version = DocumentVersion(document_id=doc.id, version_date=metadata.get("version_date", "unknown"),
        publication_date=metadata.get("publication_date", ""), source_filename=path.name, sha256=digest,
        stored_path=str(path), extracted_text=text, extraction_method=method,
        provenance={"source_url": metadata.get("source_url", ""),
                    "source_kind": metadata.get("source_kind", "user_collected_official_copy"),
                    "ingested_by": "Mitro local MVP"})
    db.add(version)
    db.flush()
    for ordinal, (citation, body) in enumerate(split_clauses(text), 1):
        db.add(Clause(version_id=version.id, citation=citation, ordinal=ordinal, text=body))
    db.commit()
    db.refresh(version)
    return {"document_id": doc.id, "version_id": version.id, "duplicate": False,
            "sha256": digest, "extraction_method": method, "clause_count": len(version.clauses)}

def bootstrap(db: Session, manifest_path: Path | None = None) -> list[dict]:
    manifest_path = manifest_path or ROOT / "sources" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    results = []
    for item in manifest["documents"]:
        source = (ROOT / item["path"]).resolve()
        if source.exists():
            results.append(ingest_file(db, source, item))
    return results

