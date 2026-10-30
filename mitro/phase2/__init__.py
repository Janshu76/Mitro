from __future__ import annotations
import ast, re
from collections import Counter
from pathlib import Path

def scan_repository(root: Path) -> dict:
    """Build Amend's deterministic Python code graph and summarize source inventory."""
    from amend.graph import build
    graph = build(root)
    serialized = graph.to_dict()
    kinds = Counter(node.get("kind", "unknown") for node in serialized["nodes"])
    files = sorted({node.get("file", "") for node in serialized["nodes"] if node.get("file")})
    findings = []
    for name, patterns in (("sensitive_logging", (r"logger?\.(?:info|warning|error|debug)\(",)),
                           ("tls_verification_disabled", (r"verify\s*=\s*False",)),
                           ("raw_sql", (r"execute\s*\(\s*f[\"']",))):
        for path in root.rglob("*.py"):
            if any(part in {".venv", "venv", "node_modules"} for part in path.parts): continue
            try: lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError: continue
            for lineno, line in enumerate(lines, 1):
                if any(re.search(pattern, line) for pattern in patterns):
                    findings.append({"rule": name, "file": path.relative_to(root).as_posix(),
                                     "line": lineno, "snippet": line.strip()[:240],
                                     "classification": "candidate_for_review"})
    return {"repository": str(root), "node_count": len(serialized["nodes"]),
            "edge_count": len(serialized["edges"]), "node_kinds": dict(kinds),
            "files_in_graph": files, "candidate_findings": findings,
            "graph": serialized,
            "limits": ["Python-oriented graph; does not perform full interprocedural or cross-language analysis.",
                       "Candidate findings require human review and approved obligations before regulatory reporting."]}

def impact_candidates(root: Path, statement: str, quote: str, citation: str) -> list[dict]:
    """Explainable lexical candidate mapping; results are leads, never compliance findings."""
    words = set(re.findall(r"[a-z][a-z0-9_]{3,}", (statement + " " + quote).lower()))
    stop = {"shall", "must", "will", "from", "under", "with", "that", "this", "where", "such", "their",
            "customer", "customers", "applicant", "application", "obligation", "regulatory", "direction"}
    words -= stop
    hits = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".sql", ".yaml", ".yml"}: continue
        if any(part in {".venv", "venv", "node_modules", "__pycache__"} for part in path.parts): continue
        try: lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError: continue
        scored = []
        for n, line in enumerate(lines, 1):
            low = line.lower()
            matches = [word for word in words if word in low]
            if matches: scored.append((n, line.strip(), matches))
        if scored:
            matched = sorted({w for _, _, ws in scored for w in ws})
            hits.append({"file": path.relative_to(root).as_posix(), "citation": citation,
                         "score": len(matched), "matched_terms": matched[:12],
                         "locations": [{"line": n, "snippet": text[:220]} for n, text, _ in scored[:5]],
                         "classification": "candidate_for_human_review"})
    return sorted(hits, key=lambda x: (-x["score"], x["file"]))[:30]
