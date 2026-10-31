"""Offline dependency update impact analysis from manifests and supplied notes."""
from __future__ import annotations
import re
from pathlib import Path

IMPORT_NAMES = {"fastapi": ("fastapi",), "sqlalchemy": ("sqlalchemy",), "pymupdf": ("fitz", "pymupdf"),
                "pypdf": ("pypdf",), "networkx": ("networkx",), "httpx": ("httpx",),
                "psycopg": ("psycopg",), "pyyaml": ("yaml",), "python-multipart": ("multipart",)}
MANIFESTS = {"requirements.txt", "pyproject.toml", "Pipfile", "Pipfile.lock", "poetry.lock",
             "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
VERSION_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+){0,3})")
BREAKING_RE = re.compile(r"(?i)breaking change|removed|removal|deprecated|deprecation|security|incompatible|migration|no longer supported")

def _manifest_matches(root: Path, package: str) -> list[dict]:
    matches = []
    key = package.lower().replace("_", "-")
    for path in root.rglob("*"):
        if not path.is_file() or path.name not in MANIFESTS or any(x in {".git", ".venv", "venv", "node_modules", "__pycache__"} for x in path.parts):
            continue
        try: content = path.read_text(encoding="utf-8", errors="replace")
        except OSError: continue
        for line_no, line in enumerate(content.splitlines(), 1):
            if re.search(rf"(?i)(?<![\w-]){re.escape(key)}(?![\w-])", line):
                matches.append({"file": path.relative_to(root).as_posix(), "line": line_no, "declaration": line.strip()[:240]})
    return matches

def analyze_dependency_update(root: Path, package: str, proposed_version: str, release_notes: str = "") -> dict:
    package = package.strip()
    if not package or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", package):
        raise ValueError("Enter a valid package name")
    if not proposed_version.strip() or len(proposed_version) > 80:
        raise ValueError("Enter a proposed version (or version range)")
    manifests = _manifest_matches(root, package)
    names = IMPORT_NAMES.get(package.lower().replace("_", "-"), (re.sub(r"[-.]+", "_", package.lower()),))
    uses = []
    for path in root.rglob("*.py"):
        if not path.is_file() or any(x in {".git", ".venv", "venv", "node_modules", "__pycache__"} for x in path.parts): continue
        try: lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError: continue
        for number, line in enumerate(lines, 1):
            if any(re.search(rf"^\s*(?:from\s+{re.escape(name)}\b|import\s+{re.escape(name)}\b)", line) for name in names):
                uses.append({"file": path.relative_to(root).as_posix(), "line": number, "import": line.strip()[:200]})
    notes = release_notes.strip()[:12000]
    flagged_notes = [line.strip()[:300] for line in notes.splitlines() if line.strip() and BREAKING_RE.search(line)]
    current_versions = sorted({v for match in manifests for v in VERSION_RE.findall(match["declaration"])})
    proposed_numbers = VERSION_RE.search(proposed_version)
    baseline_numbers = VERSION_RE.search(current_versions[0]) if current_versions else None
    if proposed_numbers and baseline_numbers:
        proposed_tuple = tuple(int(x) for x in proposed_numbers.group(1).split("."))
        baseline_tuple = tuple(int(x) for x in baseline_numbers.group(1).split("."))
        padded_new, padded_old = proposed_tuple + (0,) * (3-len(proposed_tuple)), baseline_tuple + (0,) * (3-len(baseline_tuple))
        change_level = "major" if padded_new[0] != padded_old[0] else "minor" if padded_new[1] != padded_old[1] else "patch" if padded_new[2] != padded_old[2] else "same-version"
    else:
        change_level = "baseline-unknown"
    review_attention = "high" if change_level == "major" or flagged_notes else "standard" if manifests and uses else "insufficient evidence"
    return {"package": package, "proposed_version": proposed_version.strip(), "current_versions": current_versions,
            "version_change_level": change_level, "review_attention": review_attention,
            "manifests": manifests, "code_uses": uses, "release_note_flags": flagged_notes,
            "risk": "review required" if manifests and uses else "insufficient dependency evidence",
            "analysis_mode": "local manifest and source scan; no live advisory or release-note lookup",
            "next_steps": ["Verify the proposed version and official migration guide.",
                           "Review affected imports and release-note flags.",
                           "Run dependency, compatibility, security, and regression checks in an isolated environment."],
            "release_notes_provided": bool(notes)}
