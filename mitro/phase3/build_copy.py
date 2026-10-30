"""Apply a reviewed demo patch to a separate copy and run generated tests."""
from __future__ import annotations

import os
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile

from mitro.database import DATA_DIR
from mitro.phase3.changes import LENDWISE

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "var", "node_modules", ".pytest_cache"}

def _zip_copy(project: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in project.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(project)
            if any(part in IGNORED_DIRS for part in rel.parts) or path.name == ".env":
                continue
            zf.write(path, (Path("lendwise-edited") / rel).as_posix())

def build_and_verify(proposal, proposal_id: int) -> dict:
    """Build once per proposal. Only the bundled synthetic Lendwise is executable."""
    if proposal.bundle_path and Path(proposal.bundle_path).is_file():
        return {"test_status": proposal.test_status, "test_output": proposal.test_output,
                "download_ready": True, "copy_path": proposal.copy_path}
    if not LENDWISE.is_dir():
        raise FileNotFoundError("The bundled Lendwise demo project is missing")
    run_root = DATA_DIR / "phase3" / f"proposal-{proposal_id}"
    project = run_root / "lendwise-edited"
    if run_root.exists():
        raise FileExistsError("A partial build already exists for this proposal; create a fresh proposal to retry safely")
    run_root.mkdir(parents=True)
    shutil.copytree(LENDWISE, project, ignore=shutil.ignore_patterns(*IGNORED_DIRS, ".env", "*.db"))

    for edit in proposal.edits:
        rel = PurePosixPath(edit["file"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Patch contains an unsafe file path")
        target = project.joinpath(*rel.parts)
        if not target.is_file():
            raise FileNotFoundError(f"Expected target file not found in copy: {rel}")
        source = target.read_text(encoding="utf-8")
        before = edit["before"]
        if source.count(before) != 1:
            raise ValueError(f"Target in copied project no longer matches the reviewed patch: {rel}")
        target.write_text(source.replace(before, edit["after"], 1), encoding="utf-8", newline="\n")

    tests = project / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_mitro_phase3_generated.py").write_text(proposal.test_source, encoding="utf-8", newline="\n")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(project) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_mitro_phase3_generated.py", "-v"]
    try:
        completed = subprocess.run(cmd, cwd=project, env=env, capture_output=True,
                                   text=True, timeout=45, check=False)
        output = (completed.stdout + "\n" + completed.stderr).strip()[-12000:]
        status = "passed" if completed.returncode == 0 else "failed"
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + "\n" + (exc.stderr or "") + "\nGenerated test exceeded 45 seconds.")[-12000:]
        status = "timed_out"
    evidence = {
        "proposal_id": proposal_id,
        "scenario": proposal.scenario,
        "title": proposal.title,
        "source_document": proposal.source_identifier,
        "source_citation": proposal.source_citation,
        "source_url": proposal.source_url,
        "source_sha256": proposal.source_sha256,
        "verbatim_quote": proposal.quote,
        "expected_behavior": proposal.expected_behavior,
        "generated_test": "tests/test_mitro_phase3_generated.py",
        "test_status": status,
        "test_output": output,
        "original_source_modified": False,
        "limitations": ["Synthetic demonstration only; not a regulatory finding or legal/accounting opinion.",
                        "Patch template and test behavior require qualified human review."]
    }
    (project / "MITRO_PHASE3_EVIDENCE.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    bundle = DATA_DIR / "phase3" / "downloads" / f"lendwise-edited-{proposal_id}.zip"
    _zip_copy(project, bundle)
    return {"test_status": status, "test_output": output, "download_ready": bundle.is_file(),
            "copy_path": str(project), "bundle_path": str(bundle)}
