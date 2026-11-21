import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from mitro.db import RegulatoryDocument, DocumentVersion, Clause
from mitro.phase1.parser import extract_pdf_document, split_page_clauses, sha256_file, fitz

ROOT = Path(__file__).resolve().parents[2]

def ingest_file(db: Session, path: Path, metadata: dict) -> dict:
    path = path.resolve()
    pages, method, extraction = extract_pdf_document(path)
    text = "\n\n".join(pages)
    digest = sha256_file(path)
    artifact_dir = ROOT / "data" / "extractions"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{digest}.json"
    extraction_payload = {"page_text": pages, **extraction}
    extraction_payload["processing_history"] = [{"processed_at": datetime.now(timezone.utc).isoformat(),
        "method": method, "sha256": digest}]
    artifact_path.write_text(json.dumps(extraction_payload, ensure_ascii=False, default=str), encoding="utf-8")
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
                    "ingested_by": "Mitro local MVP", "page_count": len(pages),
                    "parser_versions": extraction.get("parser_versions", {}),
                    "processing_history": extraction_payload["processing_history"],
                    "structured_artifact": str(artifact_path),
                    "structured_extraction": "docling" if extraction.get("structured_document") else "page_text_only",
                    "structured_warning": extraction.get("structured_warning", ""),
                    "page_status": [{"page": i, "text_characters": len(page),
                        "status": "text_extracted" if page.strip() else "no_text_detected",
                        "confidence": extraction.get("page_confidence", [0.0] * len(pages))[i - 1]}
                        for i, page in enumerate(pages, 1)],
                    "extraction_warning": "OCR output requires human verification" if "needs-human-verification" in method or "needs-ocr" in method else ""})
    db.add(version)
    db.flush()
    original_pdf = fitz.open(path) if path.suffix.lower() == ".pdf" and fitz is not None else None
    for ordinal, (citation, body, page_number) in enumerate(split_page_clauses(pages), 1):
        bboxes = []
        try:
            if original_pdf is not None and body and 0 < page_number <= len(original_pdf):
                bboxes = [[round(float(v), 2) for v in rect]
                          for rect in original_pdf[page_number - 1].search_for(body[:100])[:12]]
        except Exception:
            bboxes = []
        db.add(Clause(version_id=version.id, citation=citation, ordinal=ordinal, text=body,
                      page_number=page_number, coordinates=bboxes))
    if original_pdf is not None:
        original_pdf.close()
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

