"""Read-only, explainable code inventory and candidate rules for local repositories."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", ".next", "dist", "build", "coverage", ".mypy_cache", ".pytest_cache"}
EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".sql", ".yaml", ".yml", ".json"}
RULES = {
    "sensitive_logging": (re.compile(r"(?:logger|log|logging)\.(?:info|warning|error|debug|exception)\s*\([^\n]*(?:\b(?:ssn|aadhaar|pan|phone|email|account|customer|token|password|secret|dob)\b)", re.I), "high", "Sensitive-looking values may be written to logs."),
    "tls_verification_disabled": (re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true", re.I), "high", "TLS certificate verification appears disabled."),
    "raw_sql_interpolation": (re.compile(r"(?:execute|cursor\.execute)\s*\(\s*f[\"']|(?:SELECT|UPDATE|DELETE|INSERT)[^\n]*(?:\+\s*(?:user|customer|request|params))", re.I), "medium", "SQL may interpolate untrusted values."),
    "excessive_personal_data_fields": (re.compile(r"\b(?:aadhaar|pan_number|date_of_birth|precise_location|contacts|call_logs|device_contacts)\b", re.I), "low", "Review whether this personal-data field is necessary for the stated purpose."),
    "consent_related_code": (re.compile(r"\b(?:consent|permission|opt_in|optin|withdraw_consent)\b", re.I), "info", "Consent-related implementation location; inspect enforcement and withdrawal behavior."),
    "third_party_call": (re.compile(r"\b(?:requests\.(?:get|post|put)|httpx\.(?:get|post|put)|fetch\s*\(|axios\.(?:get|post)|urlopen\s*\()", re.I), "info", "Outbound API call; review authentication, TLS, data minimisation, and vendor oversight."),
    "retention_or_deletion_code": (re.compile(r"\b(?:retention|delete|erase|purge|expire|ttl)\b", re.I), "info", "Data lifecycle control location; confirm coverage and scheduled execution."),
}

def _source_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part.lower() in IGNORED for part in rel.parts):
            continue
        if "compliance" in {part.lower() for part in rel.parts}:
            continue
        yield path, rel

def scan_repository(root: Path) -> dict:
    """Collect source inventory, Python graph, and review-only static candidates."""
    root = root.resolve()
    files = list(_source_files(root))
    findings = []
    for path, rel in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, 1):
            for rule, (pattern, severity, explanation) in RULES.items():
                if pattern.search(line):
                    findings.append({"rule": rule, "severity": severity, "file": rel.as_posix(),
                        "line": line_no, "snippet": line.strip()[:240], "explanation": explanation,
                        "classification": "candidate_for_review"})
    # Keep Amend's graph where available; a missing/unsupported Python graph must
    # not stop the language-neutral source inventory from being useful.
    try:
        from amend.graph import build
        serialized = build(root).to_dict()
    except Exception:
        serialized = {"nodes": [], "edges": []}
    kinds = Counter(node.get("kind", "unknown") for node in serialized.get("nodes", []))
    graph_files = sorted({node.get("file", "") for node in serialized.get("nodes", []) if node.get("file")})
    return {"repository": root.name, "file_count": len(files), "files": [p.relative_to(root).as_posix() for p, _ in files[:5000]],
            "node_count": len(serialized.get("nodes", [])), "edge_count": len(serialized.get("edges", [])),
            "node_kinds": dict(kinds), "files_in_graph": graph_files,
            "candidate_findings": findings,
            "engines": ["deterministic regex candidate rules", "Amend Python graph"],
            "limits": ["Static matches are leads for human review, not proof of a vulnerability or regulatory breach.",
                       "No code is modified, executed, uploaded, or sent to an external service.",
                       "Cross-file data-flow analysis and language-specific semantic analysis are not included.",
                       "Absence of a match does not prove that a control is present."]}

def impact_candidates(root: Path, statement: str, quote: str, citation: str) -> list[dict]:
    """Explainable lexical candidate mapping; results are leads, never compliance findings."""
    synonyms = {
        "consent": {"consent", "opt_in", "permission", "withdraw"},
        "personal": {"personal", "customer", "applicant", "sensitive", "aadhaar", "pan", "phone", "email"},
        "data": {"data", "record", "information", "profile", "document"},
        "log": {"log", "logger", "logging", "audit"},
        "delete": {"delete", "erase", "purge", "retention", "expire"},
        "third": {"vendor", "partner", "third_party", "provider", "gateway", "integration"},
        "access": {"access", "authorize", "permission", "owner", "tenant", "customer_id"},
        "security": {"security", "tls", "verify", "encrypt", "token", "secret"},
    }
    raw = set(re.findall(r"[a-z][a-z0-9_]{2,}", (statement + " " + quote).lower()))
    stop = {"shall", "must", "will", "from", "under", "with", "that", "this", "where", "such", "their", "customer", "customers", "applicant", "application", "obligation", "regulatory", "direction"}
    terms = raw - stop
    expanded = set(terms)
    for key, values in synonyms.items():
        if terms & values:
            expanded |= values
    hits = []
    for path, rel in _source_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        scored = []
        for n, line in enumerate(lines, 1):
            lower = line.lower()
            matches = sorted(term for term in expanded if len(term) > 2 and term in lower)
            if matches:
                scored.append((n, line.strip(), matches))
        if scored:
            matched = sorted({word for _, _, words in scored for word in words})
            hits.append({"file": rel.as_posix(), "citation": citation, "score": len(matched),
                "matched_terms": matched[:12], "locations": [{"line": n, "snippet": text[:220]} for n, text, _ in scored[:5]],
                "classification": "candidate_for_human_review"})
    return sorted(hits, key=lambda item: (-item["score"], item["file"]))[:30]
